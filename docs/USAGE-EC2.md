# EC2

## General

Each of the scripts in this repo support the `-h` option to print out options
and usage

    docker run --rm afaws <script> -h

To run off local copy of code

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws <script> -h

Note also that you'll need to mount your ssh key into the docker container
to run scripts that execute commands via ssh


## Examples

### ec2-resources

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/ec2-resources --log-level INFO \
        -t Instance
    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/ec2-resources --log-level INFO \
        -t Instance -i test-1
    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/ec2-resources --log-level INFO \
        -t Instance -i test-* -i staging-*
    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/ec2-resources --log-level INFO \
        -t SecurityGroup -i web-ports
    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/ec2-resources --log-level INFO \
        -t Image -i ami-abc123

### elb-manage

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/elb-manage --log-level INFO -l
    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/elb-manage --log-level INFO -p test -l
    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/elb-manage --log-level INFO \
        -p test -a test-1
    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/elb-manage --log-level INFO \
        -p test -r test-1

### ec2-execute

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh afaws /afaws/bin/ec2-execute \
        --log-level INFO -k /root/.ssh/id_rsa.pem \
        -i test-1 -c 'echo foo'

### ec2-network

    (TODO: Add example)

### ec2-initialize

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh afaws /afaws/bin/ec2-initialize --log-level INFO \
        -k /root/.ssh/id_rsa.pem --config-file ./config.json -i test-2

### ec2-reboot

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh afaws /afaws/bin/ec2-reboot \
        --log-level INFO --initialize -k /root/.ssh/id_rsa.pem \
        --config-file ./config.json -i test-2



### Full life-cycle (ec2-launch / ec2-manage / ec2-shutdown)

This example adds an instance to the test pool

First, launch and initialize the instances, based off on the existing test instance

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        -v $HOME/.ssh:/root/.ssh afaws /afaws/bin/ec2-launch \
        --log-level INFO --instance test-1 -n test-2 \
        --initialize --ssh-key /root/.ssh/id_rsa.pem \
        --config-file ./config.json

Update DNS and manually test it.  Once confident that it's working, add to the
appropriate ELB pool:

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/elb-manage --log-level INFO   \
        -p test -a test-2

#### Shutting down ELB pool instances

This example removes the instance added to the test pool in the previous example

First, remove the instance from the pool

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/elb-manage --log-level INFO   \
        -p test -r test-2

Then check until drained

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/elb-manage --log-level INFO   \
        -p test -l

Once the instances are no longer listed, shut down

    docker run --rm -ti -v $PWD/:/afaws/ -v $HOME/.aws/:/root/.aws/ \
        afaws /afaws/bin/ec2-shutdown  --log-level INFO \
        -i test-2 --terminate
