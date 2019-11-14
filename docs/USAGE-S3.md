# S3

## General

See 'General' notes in [USAGE-EC2](./USAGE-EC2.md) doc.

## Examples

### s3-download

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/s3-download --log-level INFO \
        -d ./tmp -b public-data -p wetather/

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/s3-download --log-level INFO \
        -d ./tmp -b public-data -p wetather/geojson/

    docker run --rm -ti -v $PWD/:/aws/ -v $HOME/.aws/:/root/.aws/ \
        aws /aws/bin/s3-download --log-level INFO \
        -d ./tmp -b public-data -k wetather/geojson/latest.geojson
