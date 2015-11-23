import unittest2
import random
from functools import wraps
from monocyte.handler import s3 as s3_handler
from monocyte.handler import Resource


class S3Tests(unittest2.TestCase):

    def setUp(self):
        self.s3_handler = s3_handler.Bucket(lambda region_name: region_name not in [
            'cn-north-1', 'us-gov-west-1'])
        self.prefix = 'test-' + hex(random.randint(0, 2**48))[2:] + '-'
        self.our_buckets = []

        def my_filter(old_function):
            @wraps(old_function)
            def new_function(*args):
                conn, bucket, checked_buckets = args
                if not bucket.name.startswith(self.prefix):
                    print("skipping bucket {0}".format(bucket.name))
                    return
                else:
                    print("processing {0}".format(bucket.name))
                checked_buckets = []
                return old_function(conn, bucket, checked_buckets)

            return new_function

        self.s3_handler.check_if_unwanted_resource = my_filter(
            self.s3_handler.check_if_unwanted_resource
        )

    def tearDown(self):
        for resource in self.our_buckets:
            print("to be deleted {0}".format(resource.wrapped.name))
            self.s3_handler.dry_run = False
            self.s3_handler.delete(resource)

    def test_search_unwanted_resources_dry_run(self):
        self._given_bucket_mock('test-bucket', 'eu-west-1')
        self.s3_handler.dry_run = True

        resources = self.s3_handler.fetch_unwanted_resources()
        uniq_resources = self._uniq(resources)
        self.assertEqual(len(uniq_resources), 1)

        self.s3_handler.delete(uniq_resources[0])

        resources = self.s3_handler.fetch_unwanted_resources()
        uniq_resources = self._uniq(resources)
        self.assertEqual(len(uniq_resources), 1)

    def test_search_unwanted_resources_no_dry_run(self):
        self._given_bucket_mock('test-bucket', 'eu-west-1')
        self.s3_handler.dry_run = False

        resources = self.s3_handler.fetch_unwanted_resources()
        uniq_resources = self._uniq(resources)
        self.assertEqual(len(uniq_resources), 1)

        self.s3_handler.delete(uniq_resources[0])

        resources = self.s3_handler.fetch_unwanted_resources()
        uniq_resources = self._uniq(resources)
        self.assertEqual(len(uniq_resources), 0)

        # Prevent self.tearDown() from failing with "404 Not Found".
        self.our_buckets = []

    def _given_bucket_mock(self, bucket_name, region_name, create_key=False):
        conn = self.s3_handler.connect_to_region(region_name)
        bucket = conn.create_bucket(self.prefix + bucket_name,
                                    location=region_name)
        resource = Resource(resource=bucket,
                            resource_type='s3.Bucket',
                            resource_id='42',
                            creation_date='2015-11-23',
                            region=self.s3_handler.map_location(
                                region_name))
        self.our_buckets.append(resource)
        return bucket

    def _uniq(self, resources):
        found_names = []
        uniq_resources = []
        for resource in resources:
            name = resource.wrapped.name
            if name in found_names:
                continue
            uniq_resources.append(resource)
            found_names.append(name)

        return uniq_resources


if __name__ == "__main__":
    unittest2.main()
