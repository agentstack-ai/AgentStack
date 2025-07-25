# Contributing
First of all, __thank you__ for your interest in contributing to AgentStack! Even the smallest contributions help a _ton_.

Our vision is to build the defacto CLI for quickly spinning up an AI Agent project. We want to be the [create-react-app](https://create-react-app.dev/) of agents. Our inspiration also includes the oh-so-convenient [Angular CLI](https://v17.angular.io/cli).

### Exclusive Contributor Sticker
AgentStack contributors all receive a free sticker pack including an exclusive holographic sticker only available to contributors to the project :)

Once your PR is merged, fill out [this form](https://docs.google.com/forms/d/e/1FAIpQLSfvBEnsT8nsQleonJHoWQtHuhbsgUJ0a9IjOqeZbMGkga2NtA/viewform?usp=sf_link) and I'll send your sticker pack out ASAP! <3

## How to Help

Grab an issue from the [issues tab](https://github.com/AgentOps-AI/AgentStack/issues)! Plenty are labelled "Good First Issue". Fork the repo and create a PR when ready!

The best place to engage in conversation about your contribution is in the Issue chat or on our [Discord](https://discord.gg/JdWkh9tgTQ).

## Setup

1. Fork the repo from the github website or with [gh repo fork AgentOps-AI/AgentStack](https://cli.github.com/manual/gh_repo_fork)
2. Clone the forked repo and get in there!
   `ssh example`
   `git clone git@github.com:<your-github-username>/AgentStack.git`
   `cd AgentStack`
3. Install agentstack as an edtiable project and set it up for development and testing
   `pip install -e .[dev,test]`
   This will install the CLI locally and in editable mode so you can use `agentstack <command>` to test your latest changes

## Adding Tools
If you're reading this section, you probably have a product that AI agents can use as a tool. We're glad you're here!

Adding tools is easy once you understand the project structure. Our documentation for adding tools is available on our hosted docs [here](https://docs.agentstack.sh/contributing/adding-tools).

## Before creating your PR
Be sure that you are opening a PR using a branch other than `main` on your fork. This enables us
to pull your branch and make modifications to the PR with your permission that may be helpful.

### Formatting
AgentStack uses Ruff formatter for consistent code formatting. To format your code, run:
```bash
pip install ruff
ruff format .
```

### Type Checking
AgentStack uses MyPy for type checking. To check types, run:
```bash
mypy agentstack
```

### Pre-Commit Hooks
Ruff and MyPy can be run as pre-commit hooks. To enable these hooks, run:
```bash
pre-commit install
```

## Tests
CLI tests are a bit hacky, so we are not tracking coverage. 
That said, _some_ testing is required for any new functionality added by a PR.

Tests MUST pass to have your PR merged. We _will not_ allow main to be in a failing state, so if your tests are failing, this is your problem to fix.

### Run tests locally
Install the testing requirements
```bash
pip install 'agentstack[test]'
```

Then run tests in all supported python versions with
```bash
tox
```

## Need Help?
If you're reading this, we're very thankful you wanted to contribute! I understand it can be a little overwhelming to 
get up to speed on a project like this and we are here to help!

### Open a draft PR
While we can't promise to write code for you, if you're stuck or need advice/help, open a draft PR and explain what you were trying to build and where you're stuck! Chances are, one of us have the context needed to help you get unstuck :)

### Chat on our Discord
We have an active [Discord server](https://discord.gg/JdWkh9tgTQ) with contributors and AgentStack users! There is a channel just for contributors on there. Feel free to drop a message explaining what you're trying to build and why you're stuck. Someone from our team should reply soon!

# Thank You!
The team behind AgentStack believe that the barrier to entry for building agents is far too high right now! We believe that this technology can be streamlined and made more accessible. If you're here, you likely feel the same! Any contribution is appreciated.

If you're looking for work, we are _always_ open to hiring passionate engineers of all skill levels! While closing issues cannot guarantee an offer, we've found that engineers who contribute to our open source repo are some of the best we could ever hope to find via recruiters! Be active in the community and let us know you're interested in joining the team!