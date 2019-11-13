import logging
import os

import boto3
import botocore

class S3Downloader(object):

    def __init__(self, dest_dir, bucket_name, **kwargs):
        if not os.path.isdir(dest_dir) and not kwargs.get("create_dest_dir"):
            raise RuntimeError("Desination dir {} does not exist".format(dest_dir))
        self.dest_dir = dest_dir

        s3 = boto3.resource('s3')
        self.bucket = s3.Bucket(bucket_name)
        self.bucket_name = bucket_name

        self.mirror_s3_path =  kwargs.get('mirror_s3_path')

        self.local_bucket_dir = (os.path.join(dest_dir, bucket_name)
            if self.mirror_s3_path else dest_dir)

        if not os.path.exists(self.local_bucket_dir):
            os.makedirs(self.local_bucket_dir)

    def download_all(self, path):
        path = path.strip('/')
        for o in self.bucket.objects.all():
            if not path or o.key.startswith(path):
                self.download_one(o.key, path=path)

    def download_one(self, key, path=None):
        # strip path just in case called by client directly with path defined
        path = path.strip('/')
        key = key.lstrip('/')

        logging.info("Downloading %s > %s", self.bucket_name, key)

        # TODO: check size and warn user if over some threshold
        local_file_name = os.path.join(self.local_bucket_dir, key)
        if not self.mirror_s3_path and path:
            local_file_name = local_file_name.replace(path+'/', '')

        local_dir = os.path.dirname(local_file_name)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        try:
            self.bucket.download_file(key, local_file_name)

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                logging.error("*** %s > %s does not exist",
                    self.bucket_name, key)
            else:
                logging.error("*** Failed to download %s > %s",
                    self.bucket_name, key)
