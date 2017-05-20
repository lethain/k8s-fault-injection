"""
Proof of concept around simple fault injection for Kubernetes.
"""
import argparse
import pprint
import random
import requests


class KClient(object):
    "Kubernetes client."
    default_cert_path = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
    default_token_path = '/var/run/secrets/kubernetes.io/serviceaccount/token'

    def __init__(self, loc, cert_path=None, token_path=None):
        self.loc = loc
        self.cert_path = cert_path or self.default_cert_path
        self.token_path = token_path or self.default_token_path

    def session(self):
        "Build requests.Session."
        s = requests.Session()
        if self.loc.startswith('https://'):
            s.verify = self.cert_path
            if not use_proxy:
                with open(self.token_path, 'r') as token_fin:
                    s.headers = {'Authorization': 'Bearer %s' % token_fin.read()}
        return s

    def request(self, method, path, *args, **kwargs):
        "Perform request."
        url = "%s%s" % (self.loc, path)
        return self.session().request(method, url, *args, **kwargs)

    def get(self, path, *args, **kwargs):
        "Perform GET."
        return self.request('get', path, *args, **kwargs)

    def delete(self, path, *args, **kwargs):
        "Perform DELETE."
        return self.request('delete', path, *args, **kwargs)


def deployments(kc, include_by_default=False, ignore_namespaces=None):
    """
    Build list of deployments to consider. This is done by scanning all
    deployments and checking the `fault_injection.opt_in` annotation.

    If ignore_by_default is true, then ignore_namespaces is not used,
    and only deployments with explicit `opt_in: true` or `opt_out: true`
    flags will be considered.

    `ignore_namespaces` will cause the listed namespaces to behave as if
    `include_by_default = False`, even when the default behavior is `include_by_default = True`.
    That also means, that `ignore_namespaces` doesn't have any behavior if `include_by_default = False`.
    """
    deps = kc.get("/apis/extensions/v1beta1/deployments").json()['items']

    enabled = []
    for dep in deps:
        meta = dep.get('metadata', {})
        name = meta.get('name', 'missing-name')
        namespace = meta.get('namespace', 'missing-namespace')
        annotations = dep['metadata']['annotations']
        opt_in = annotations.get('fault_injection.opt_in', None)
        opt_out = annotations.get('fault_injection.opt_out', None)

        if namespace in ignore_namespaces:
            continue
        if opt_out:
            continue
        if (not include_by_default) and not opt_in:
            continue
        enabled.append(dep)
    return enabled


def pods(kc, deployment):
    "Retrieve pods for a deployment."
    metadata = deployment.get('metadata', {})
    labels = metadata.get('labels', {})
    if 'app' in labels:
        pods = kc.get('/api/v1/pods?labelSelector=app%%3D%s' % (labels['app'],))
        return pods.json()['items']
    return []


def inject_faults(loc, include_by_default, ignore_namespaces, dry_run):
    kc = KClient(loc)

    deleted_pods = 0
    total_pods = 0
    for dep in deployments(kc, include_by_default, ignore_namespaces):
        meta = dep.get('metadata', {})
        annotations = meta.get('annotations', {})
        max_to_delete = int(annotations.get('fault_injection.max_to_delete', '1'))

        # deleting because it's too noisy to print, no change to behavior
        del annotations['kubectl.kubernetes.io/last-applied-configuration']

        print "deployment: %s" % (meta['name'],)
        ps = pods(kc, dep)
        num_to_delete = 1
        to_delete = random.sample(ps, num_to_delete)

        deleted_pods += len(to_delete)
        total_pods += len(ps)

        names = ", ".join([p['metadata']['name'] for p in to_delete])
        print "selected %s of %s pods: %s" % (len(to_delete), len(ps), names)

        if dry_run:
            print 'dry_run enabled, so not taking any actions'
        else:
            for p in to_delete:
                link = p['metadata']['selfLink']
                print "\tDELETE %s" % (link,)
                kc.delete(link)

    print "\ndeleted %s out of %s considered pods" % (deleted_pods, total_pods)


def main():
    "For use as CLI."
    p = argparse.ArgumentParser(description='Inject faults into Kubernetes.')
    p.add_argument('--loc', default='https://kubernetes', help='location to access Kubernetes API')
    p.add_argument('--include-by-default', default=False, action='store_true', help='opt all deploys in by default')
    p.add_argument('--ignore', default='kube-system', help='csv of namespaces to ignore')
    p.add_argument('--dry-run', default=False, action='store_true', help='don\'t perform any actions')

    args = p.parse_args()
    inject_faults(args.loc, args.include_by_default, args.ignore.split(','), args.dry_run)


if __name__ == '__main__':
    main()
