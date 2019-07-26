#!/bin/bash


# Stop on error.
set -e

# Setup.
pip install httpie

# Check out a new branch for the new version.
git checkout -b new-branch

# Configure git.
git configure user.name "$GIT_AUTHOR_NAME"
git configure user.email "$GIT_AUTHOR_EMAIL"

# Bump version.
tox -e bump

# Set an environment variable with the new version number.
new_version="$(git describe)"

# Rename the new git branch to the version number.
git branch -m "${new_version}"

# Add remote.
git remote add origin https://"${GITHUB_TOKEN}"@github.com/"${REPO_OWNER}"/"${REPO_NAME}".git

# Push to remote branch.
git push --set-upstream origin "$new_version"  --follow-tags

# Open a pull request from the new branch into `release` branch.
# Write the json output into a file.
http \
    -a "${GITHUB_USERNAME}":"${GITHUB_TOKEN}" \
    --json \
    POST https://api.github.com/repos/"${REPO_OWNER}"/"${REPO_NAME}"/pulls  \
    title="Merge new version: ${new_version}" \
    head="${new_version}" \
    base="release" \
    | tee posted_pull_request.json

# Show the file contents.
cat posted_pull_request.json

# Extract the issue number from the pull request.
issue_number="$(jq '.issue_number' < posted_pull_request.json)"

# Show the pull request number.
echo Pull request: "$issue_number"

# Add the `merge` label to the pull request so that probot-auto-merge will rebase and merge it.
http \
    -a "${GITHUB_USERNAME}":"${GITHUB_TOKEN}" \
    --json \
    POST https://api.github.com/repos/"${REPO_OWNER}"/"${REPO_NAME}"/issues/"${issue_number}"/labels \
    labels="merge"
