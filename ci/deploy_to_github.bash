#!/bin/bash


# Stop on error.
set -euo pipefail

echo Setup.
pip install httpie

echo Check out a new branch for the new version.
git checkout -b new-branch

echo Configure git.
git config user.name "$GIT_AUTHOR_NAME"
git config user.email "$GIT_AUTHOR_EMAIL"

echo Bump version.
tox -e bump

echo Set an environment variable with the new version number.
new_version="$(git describe)"


echo Rename the new git branch to the version number.
git branch -m "${new_version}"


echo Add remote.
git remote add authorized-origin https://"${GITHUB_TOKEN}"@github.com/"${REPO_OWNER}"/"${REPO_NAME}".git

echo Push to remote branch.
git push --set-upstream authorized-origin "$new_version"  --follow-tags

echo Open a pull request from the new branch into release branch.
echo Write the json output into a file.
http \
    -a "${GITHUB_USERNAME}":"${GITHUB_TOKEN}" \
    --json \
    POST https://api.github.com/repos/"${REPO_OWNER}"/"${REPO_NAME}"/pulls  \
    title="Merge new version: ${new_version}" \
    head="${new_version}" \
    base="release" \
    >posted_pull_request.json \
    2>/dev/null

echo Show the file contents.
cat posted_pull_request.json

echo Extract the issue number from the pull request.
issue_number="$(jq '.number' < posted_pull_request.json)"

echo Show the pull request number.
echo Pull request: "$issue_number"

echo Add the _merge_ label to the pull request so that probot-auto-merge will rebase and merge it.
http \
    -a "${GITHUB_USERNAME}":"${GITHUB_TOKEN}" \
    --json \
    POST https://api.github.com/repos/"${REPO_OWNER}"/"${REPO_NAME}"/issues/"${issue_number}"/labels \
    labels:='["merge"]' \
    &>/dev/null
