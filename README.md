# AWS automation

## Build docker containers

    docker build -t aws .


## API credientials and IAM

The `aws` package looks for AWS API key and secret in
`/root/.aws/credentials`.  You'll need to set up an account (or
AIM user) with appropriate permissions, and  create API credentials. Go to
https://console.aws.amazon.com/iam/home?region=us-west-2#/users to do that.

You'll then need to create a `.aws/` dir somewhere, create a credentials
file under that dir, and mount that dir to `/root/.aws/` in your docker
containers


## Configuration

TODO: fill in this section once configuration is figured out


## Python session

Use docker to start an ipython session with all dependency python packages
and the local code available and importable:

    docker run --rm -ti \
        -v $PWD/:/aws/ \
        -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh \
        aws ipython


## Usage:

 - [EC2 scripts](USAGE-EC2.md)
