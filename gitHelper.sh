#!/bin/sh

function MAKE_PULL_REQUEST(){
	clear
	echo "enter the feature branch you would like to merge into dev branch"
	read feature_branch 

	read -p "Are you sure you want to merge ${feature_branch} into dev? (press 'y' if you want to procced) " check

	if [[ "${check}" = "y" ]]; then
		echo "performing merge to dev branch.."
		git checkout develop
		git pull
		git merge "${feature_branch}"
		merge_out=$?
		if [[ merge_out -eq 0 ]]; then
		git push
		echo "Merge of ${feature_branch} to dev was a success!"
		read -p "Press ENTER if you wish to move forward and create a Release branch from the current dev branch(CTRL+C to quit)" create_rb_check
			if [[ $? -eq 0 && $create_rb_check = "" ]]; then
				MAKE_RELEASE_BRANCH
			fi
		else
			echo "An issue occured with the merge, failed to procced!"
			echo "Please verify the feature branch name or stash\checkout unsaved files!"
			return 1
		fi
	else
		echo "script will now exit, merge did not took place"
		return 1
	fi
}

function MAKE_RELEASE_BRANCH(){
	echo "Please provide a name for the Release branch"
	echo "Be sure to follow the convention: release/{major}.{minor}.{patch}"
	regex='release\/[0-9].[0-9].[0-9]' #Needs fix!
	read release_branch
	if [[ "$release_branch" =~ $regex ]]; then
		echo "Creating a Release branch from current dev with the name: ${release_branch}"
		git checkout develop
		git checkout -b $release_branch
		git push --set-upstream origin "${release_branch}" 
		echo "Release branch ${release_branch} was created!"
		read -p "Press ENTER if you wish to move forward and promote the new Release branch to the master (CTRL+C to quit)" create_pb_check
		if [[ $? -eq 0 && $create_rb_check = "" ]]; then
			PROMOTE_RELEASE
		fi
	else
		clear
		echo "${release_branch} does not follow the naming convention!"
		MAKE_RELEASE_BRANCH
	fi
}

function PROMOTE_RELEASE(){
	clear
	if [[ -z "$release_branch" ]]; then
		echo "Please provide a name for the Release branch"
		read release_branch
	fi

	read -p "Are you sure you want to promote ${release_branch} into master? (press 'y' if you want to procced) " master_check

	if [[ "${master_check}" = "y" ]]; then
		echo "Promoting to master: merging to master + tagging master + delete ${release_branch}"
		git checkout master
		git merge "${release_branch}"
		git tag -a "${release_branch}" -m "Merged release branch: ${release_branch}" HEAD
		git branch -D "${release_branch}"
		git push
		git push origin tag "${release_branch}"
		git push origin --delete "${release_branch}"
		echo "Promote has succeeded!!"
	fi
}

function HELP(){
	echo 'This script can assist with creating a PR, create a Realse branch, and Promote it to master'
	echo
	echo "Syntax: ./gitHelper [-h|pull_r|rb|pr]"
	echo
	echo "h         Present this help page"
	echo "pull_r    Creates a Pull request from a feature branch and merge it to Develop branch"
	echo "rf        Creates a Release branch flow from the current Develop branch"
	echo "pr        Promote a release branch to master,tag it and deletes the release branch"
	echo


}

case "$1" in
  -h) 
     HELP
     exit;;
  -pull_r) 
     MAKE_PULL_REQUEST
     exit;;
  -rf) 
     MAKE_RELEASE_BRANCH
     exit;;
  -pr) 
     PROMOTE_RELEASE
     exit;;

esac

HELP
