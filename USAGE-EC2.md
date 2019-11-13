# EC2

## General

Each of the scripts in this repo support the `-h` option to print out options
and usage

    docker run --rm aws <script> -h

To run off local copy of code

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws <script> -h

Note also that you'll need to mount your ssh key into the docker container
to run scripts that execute commands via ssh


## Examples

### ec2-resources

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/ec2-resources --log-level INFO \
        -t Instance
    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/ec2-resources --log-level INFO \
        -t Instance -i test-1
    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/ec2-resources --log-level INFO \
        -t Instance -i test-* -i staging-*
    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/ec2-resources --log-level INFO \
        -t SecurityGroup -i bluesky-web
    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/ec2-resources --log-level INFO \
        -t Image -i ami-abc123

### elb-manage

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/elb-manage --log-level INFO -l
    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/elb-manage --log-level INFO -p test -l
    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/elb-manage --log-level INFO \
        -p test -r test-1
    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/elb-manage --log-level INFO \
        -p test -a test-1

### elb-execute

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh aws /aws/bin/ec2-execute \
        --log-level INFO -k /root/.ssh/id_rsa.pem \
        -i test-1 -c 'echo foo'

### ecs-network

    (TODO: Add example)

### elb-initialize

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh aws /aws/bin/ec2-initialize --log-level INFO \
        -k /root/.ssh/id_rsa.pem -i test-2

### elb-reboot

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh aws /aws/bin/ec2-reboot \
        --log-level INFO --initialize -k /root/.ssh/id_rsa.pem \
        -i test-2



### Full life-cycle (ec2-launch / ec2-manage / ec2-shutdown)

This example adds an instance to the test pool

First, launch and initialize the instances, based off on the existing test instance

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh aws /aws/bin/ec2-launch \
        --log-level INFO --instance test-1 -n test-2 \
        --initialize --ssh-key /root/.ssh/id_rsa.pem

Update DNS and manually test it.  Once confident that it's working, add to the
appropriate ELB pool:

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/elb-manage --log-level INFO   \
        -p test -a test-2

#### Shutting down ELB pool instances

This example removes the instance added to the test pool in the previous example

First, remove the instance from the pool

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/elb-manage --log-level INFO   \
        -p test -r test-2

Then check until drained

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/elb-manage --log-level INFO   \
        -p test -l

Once the instances are no longer listed, shut down

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/ec2-shutdown  --log-level INFO \
        -i test-2 --terminate
