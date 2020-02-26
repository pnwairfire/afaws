## API credientials and IAM

The `aws` package looks for AWS API key and secret in
`/root/.aws/credentials`.  You'll need to set up an account (or
AIM user) with appropriate permissions, and  create API credentials. Go to
https://console.aws.amazon.com/iam/home?region=us-west-2#/users to do that.

You'll then need to create a `.aws/` dir somewhere, create a credentials
file under that dir, and mount that dir to `/root/.aws/` in your docker
containers


## Configuration

Create a file, `config.json` in the root of this repo, with the following contents, modified appropriately:

```
{
    "config": {
        "iam_instance_profile": {
            "Arn": "arn:aws:iam::abc123:instance-profile/aws-automator-ssm-role",
            "Name": "role-name"
        },
        "per_instance_security_group_rules": [
            ["security-group", true, "tcp", 99997, 99998]
        ],
        "default_efs_volumes": [
            ["fs-abc123.efs.us-west-2.amazonaws.com:/", "/foo/bar/"]
        ],
        "makefile_root_dirs": [
            "/path/to/projects/with/Makefiles/"
        ],
        "docker_compose_yaml_root_dirs": [
            "/path/to/dir/with/docker-compose/yaml/files/",
            "/another/pathx/"
        ]
    }
}
```


## Build docker image

    docker build -t afaws .


## Python session

Use docker to start an ipython session with all dependency python packages
and the local code available and importable:

    docker run --rm -ti \
        -v $PWD/:/afaws/ \
        -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh \
        afaws ipython


## Installing python package via pip

    pip install --extra-index https://pypi.airfire.org/simple afaws==0.1.6
