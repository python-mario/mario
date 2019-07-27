workflow "merge_and_cleanup" {
  on = "pull_request"
  resolves = ["when tests pass, merge and cleanup"]
}

action "when tests pass, merge and cleanup" {
  uses = "python-mario/auto_merge_my_pull_requests@development"
  secrets = ["GITHUB_TOKEN"]
}
