import os
import time
import re
import requests
import json
import sqlite3
from slackclient import SlackClient 

print "test2"
"""
Make sure you have exported the following as ENV variables before starting the Bot:
Slack bot token (SLACK_BOT_TOKEN)
Zendesk api token (ZEN_TOKEN)
Jira api token (JIRA_TOKEN)
"""
# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command , channel and the user called the bot.
        If its not found, then this function returns None, None , None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            direct_user = event["user"]
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"] , direct_user
    return None, None , None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned (Bot ID). If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def get_email_from_db (slack_user):
    """
    Function will return the Slack user his email address as he entred in the 'login' command.
    """
    try:
        conn = sqlite3.connect('slackusers.db')
        conn.text_factory = bytes
        c = conn.cursor()
        c.execute("SELECT email FROM users where userId= ?", (slack_user,))
        email_value = c.fetchone()
        conn.close()
        return email_value
    except:
        return None

def handle_command(command,user):
    """
        Bot will recognize whoever called him, and will ask for his email address.
        Then, the details will be saved in sqlite db, and the command will be executed
    """
    # Finds and executes the given command, filling in response

    if command.startswith('i love you'):
        response = 'I love you more :heart:'
        return response
    # Pulls a random Joke :)
    if (command.find('joke') != -1) or (command.find('one more') != -1) :
        jokes = requests.get('https://geek-jokes.sameerkumar.website/api')
        text = json.loads(jokes.text)
        return text
    #Login Command
    if command.startswith('login'):
        if command.endswith("?"):
            response = 'Please login with your *email address* in order to use the other commands.\nYou can also view which account you are logged in with by typing the command without arguments.\nExample: `login <email_address>`'
            return response
        conn = sqlite3.connect('slackusers.db')
        conn.text_factory = bytes
        c = conn.cursor()
        c.execute("SELECT email FROM users where userId= ?", (user,))
        email_value = c.fetchone()
        if email_value != None:
            response = ('You are already logged in with the following mail: {}'.format(email_value) +'\nIf you want to sign in with a different email, please use the `logoff` command')
        else:
            email_log = re.search (r'[\w\.-]+@[takipi.com$]+',command)
            email_log2 = re.search (r'[\w\.-]+@[overops.com$]+',command)
            if email_log != None:
                c.execute ("INSERT INTO users VALUES (?,?)" , (user,email_log.group(0)))
                conn.commit()
                response = 'Thank you for logging in! \nYou have logged in with the following email: '+email_log.group(0)+ '\nYou may now use the other commands.'
            elif email_log2 != None:
                c.execute ("INSERT INTO users VALUES (?,?)" , (user,email_log2.group(0)))
                conn.commit()
                response = 'Thank you for logging in! \nYou have logged in with the following email: '+email_log2.group(0)+ '\nYou may now use the other commands.' 
            else:
                response = 'Are you sure you have entered a valid email? \nAddress *must* finish with _@takipi.com_ or _@overops.com_'
        conn.close()
        return response
    #Logoff Command
    if command.startswith('logoff'):
        if command.endswith("?"):
            response = 'This command will remove the email address you have signed in with.\nSimply type the command to logoff.\nExample: `logoff`'
            return response
        conn = sqlite3.connect('slackusers.db')
        c = conn.cursor()
        c.execute("SELECT email FROM users where userId= ?", (user,))
        email_value = c.fetchone()
        if email_value != None:
            c.execute ("DELETE FROM users where userId = ?", (user,))
            conn.commit()
            response = 'You have successfully logged off.\nYou may now login with a different email.'
        else:
            response = 'Looks like you are already signed out.\nPlease login.'
        conn.close()
        return response
    #Jira Info Command
    if command.startswith('jira_info'):
        if command.endswith("?"):
            response = 'This command will show you all issues you have reported in the Jira system. \nTo do so, make sure you have logged in, and simply type the command. \nFor example:`jira_info`'
            return response
        temp_email = str(get_email_from_db(user))
        email_len = len(temp_email)
        email = temp_email[2:email_len-3]
        if len(email) != 0:
            try:
                jira_api = requests.get('https://overopshq.atlassian.net/rest/api/3/search?jql=reporter="'+email+'"',auth=('asaf.meytal@takipi.com', os.environ.get('JIRA_TOKEN')))
                jira_api_dic = json.loads(jira_api.text)
                temp_response_jira=[]
                i=0
                #Following loop and if's will check if issue is marked as 'Done' and if ENG was assigned.
                for i in range (len(jira_api_dic['issues'])):
                    if jira_api_dic['issues'][i]['fields']['status']['name'] == 'Done':
                        if jira_api_dic['issues'][i]['fields']['assignee'] is not None:
                            temp_response_jira.append('Subject: '+jira_api_dic['issues'][i]['fields']['summary']+
                            '\nENG Assigned: '+jira_api_dic['issues'][i]['fields']['assignee']['displayName']+
                            '\nENG Status: '+jira_api_dic['issues'][i]['fields']['status']['description']+
                            '\nCurrent Status: *'+jira_api_dic['issues'][i]['fields']['status']['name']+ 
                            '* :tada:\nCustomer: {0}'.format(jira_api_dic ['issues'][i]['fields']['customfield_10080'])+
                            '\nLink: <https://overopshq.atlassian.net/browse/'+jira_api_dic['issues'][i]['key']+'|'+jira_api_dic['issues'][i]['key']+'>')
                        else:
                            temp_response_jira.append('Subject: '+jira_api_dic['issues'][i]['fields']['summary']+
                            '\nENG Assigned: None \nENG Status: '+jira_api_dic['issues'][i]['fields']['status']['description']+
                            '\nCurrent Status: *'+jira_api_dic['issues'][i]['fields']['status']['name']+ 
                            '* :tada:\nCustomer: {0}'.format(jira_api_dic ['issues'][i]['fields']['customfield_10080'])+
                            '\nLink: <https://overopshq.atlassian.net/browse/'+jira_api_dic['issues'][i]['key']+'|'+jira_api_dic['issues'][i]['key']+'>')                            
                    else:
                        if jira_api_dic['issues'][i]['fields']['assignee'] is not None:
                            temp_response_jira.append('Subject: '+jira_api_dic['issues'][i]['fields']['summary']+
                            '\nENG Assigned: '+jira_api_dic['issues'][i]['fields']['assignee']['displayName']+
                            '\nENG Status: '+jira_api_dic['issues'][i]['fields']['status']['description']+
                            '\nCurrent Status: '+jira_api_dic['issues'][i]['fields']['status']['name']+ 
                            '\nCustomer: {0}'.format(jira_api_dic ['issues'][i]['fields']['customfield_10080'])+
                            '\nLink: <https://overopshq.atlassian.net/browse/'+jira_api_dic['issues'][i]['key']+'|'+jira_api_dic['issues'][i]['key']+'>')
                        else:
                            temp_response_jira.append('Subject: '+jira_api_dic['issues'][i]['fields']['summary']+
                            '\nENG Assigned: None \nENG Status: '+jira_api_dic['issues'][i]['fields']['status']['description']+
                            '\nCurrent Status: '+jira_api_dic['issues'][i]['fields']['status']['name']+ 
                            '\nCustomer: {0}'.format(jira_api_dic ['issues'][i]['fields']['customfield_10080'])+
                            '\nLink: <https://overopshq.atlassian.net/browse/'+jira_api_dic['issues'][i]['key']+'|'+jira_api_dic['issues'][i]['key']+'>')                            
                name = re.split('@',str(email))
                response = 'Hi '+name[0]+'!\n Here are all the issues reported by you on Jira:\n\n'
                response += ("\n ****** \n ".join(temp_response_jira))
                return response
            except Exception as e:
                print(e)
        else:
            response = 'There was an issue getting your information.\nAre you sure you have *logged in* with the correct mail (@takipi or @overops)?'
            return response
    #Jira New Command
    if command.startswith('jira_new'):
        try:
            if command.endswith('?'):
                response= 'This command will create a new Jira issue.\n You *MUST* separate the *subject* and *description* so I can tell which is which,ALL in the same line.\nThe issue will be assigned under the "Product" project,as a bug.\nExample: `jira_new subject:<your_subject here> description:<your_description_here`'
                return response
            temp_email = str(get_email_from_db(user))
            email_len = len(temp_email)
            email = temp_email[2:email_len-3]
            if len(email) != 0 :
                sub_index = command.find('subject')
                des_index = command.find('description')
                if (sub_index!= -1) and (des_index != -1):
                    subject = str(command[sub_index+8:des_index])
                    description = str(command[des_index+12:100])
                    head= {
                    "Content-Type" : "application/json"
                    }
                    data = {
                        "fields": {
                        "project":
                        {
                            "key": "PRD"
                        },
                        "summary": subject,
                        "description": "*Issue was opened with Juno.*\n"+description+".",
                        "issuetype": {
                            "name": "Bug"
                            }
                        }
                    }
                    new_issue = requests.post('https://overopshq.atlassian.net/rest/api/2/issue',headers=head,data=json.dumps(data), auth=('asaf.meytal@takipi.com','Ksw***'))
                    content = json.loads(new_issue.text)
                    id = content['key']
                    link = 'https://overopshq.atlassian.net/browse/'+id
                    response = 'A new Jira issue has been created successfully! \nGo check it out <'+link+'|here!>'
                    return response
                else:
                    response = ('Please make sure you have entered both "subject" AND "description" values.')
                    return response
            else:
                response = 'There was an issue finishing your request.\nAre you sure you have *logged in* with a correct mail (ends with:@takipi or @overops)?'
                return response
        except Exception as e:
            print(e)
    #Zendesk Command
    if command.startswith('zendesk'):
        if command.endswith("?"):
            response = 'This command will give you information about Zendesk tickets. \n Once you have logged in, simply type the command to view all of your current open cases. \nYou can also write a case number to view its 3 last comments (newest comments will show at the top). \n For example: `zendesk`  or `zendesk <case_number>`'
            return response
        case_num = re.search(r'\d\d\d\d$',command)
        if case_num != None:
            try:
                case_api = requests.get('https://takipi.zendesk.com/api/v2/tickets/'+ str (case_num.group(0))+'.json', auth=('asaf.meytal@takipi.com/token', os.environ.get('ZEN_TOKEN')))
                case_api_dic = json.loads(case_api.text)
                temp_response=[]
                subject = case_api_dic['ticket']['subject']
                priority = case_api_dic['ticket']['priority']
                org_id = case_api_dic['ticket']['organization_id']
                org_name_api = requests.get('https://takipi.zendesk.com/api/v2/organizations/'+str(org_id)+'.json',auth=('asaf.meytal@takipi.com/token', os.environ.get('ZEN_TOKEN')))
                org_name_api_dic = json.loads(org_name_api.text)
                org_name = org_name_api_dic['organization']['name']
                temp_response.append('Subject: '+ str(subject))
                temp_response.append ('Priority: '+ str(priority))
                temp_response.append ('Company: '+str(org_name))
                comments_api = requests.get('https://takipi.zendesk.com/api/v2/tickets/'+ str (case_num.group(0))+'/comments.json?sort_order=desc', auth=('asaf.meytal@takipi.com/token', os.environ.get('ZEN_TOKEN')))
                comments_api_dic = json.loads(comments_api.text)
                i = 0
                for i in range (4):
                    if comments_api_dic['comments'][i]['public'] == False:
                        temp_response.append('* *INTERNAL REPLY* *\nUpdated at: '+comments_api_dic['comments'][i]['created_at']+'\n\n'+ comments_api_dic['comments'][i]['body'])
                    else:
                        temp_response.append('Updated at: '+comments_api_dic['comments'][i]['created_at']+'\n\n'+ comments_api_dic['comments'][i]['body'])                    
                response= ("\n ****** \n ".join(temp_response))
                return response
            except:
                response = 'Please make sure you have entered a valid Zendesk case number'
                return response
        else:
            temp_email = str(get_email_from_db(user))
            email_len = len(temp_email)
            email = temp_email[2:email_len-3]
            if len(email) != 0 :
                api_zn = requests.get('https://takipi.zendesk.com/api/v2/search.json?query=type:ticket status<solved assignee:'+(email), auth=('asaf.meytal@takipi.com/token', os.environ.get('ZEN_TOKEN')))
                api_zn_dic = json.loads(api_zn.text)
                my_cases = []
                for case in api_zn_dic['results']:
                    my_cases.append('Case ID: <https://takipi.zendesk.com/agent/tickets/'+ str(case['id'])+'|'+str(case['id'])+
                    '>; Subject: *' + str(case['subject']) +
                    '* ;Priority: *' + str(case['priority'])+'*')
                name = re.split('@',str(email))
                answer='Hi '+ name[0] +'!\nHere are all of your opened cases: \n'
                answer += '\n'.join(my_cases)
                return answer
            else:
                response = 'There was an issue getting your information.\nAre you sure you have *logged in* with the correct mail (@takipi or @overops)?'
                return response
        
    response = "Hi,I am Juno, the Support Bot!:robot_face: \nI can assist with daily tasks, but I will need your email address first.\nPlease login to the system using the `login` command followed by your email address.\nThen you will be able to use the other commands I know:`zendesk`,`jira_info`,`jira_new` \n All commands have a brief explanations, simply type the command and finish it with a '?' \nPS - I know jokes as well!:grinning_face_with_one_large_and_one_small_eye:"
    return response


# Sends the response back to the channel
def send_response(result,channel):
    slack_client.api_call(
    "chat.postMessage",
    channel=channel,
    text=result
    )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Juno is up and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel , direct_user = parse_bot_commands(slack_client.rtm_read())
            if command:
                result = handle_command(command.lower(),direct_user)
                send_response (result,channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")