
There are a handful of ways to configure which deployments are eligible for fault injection.
The recommended starting place is to add the `fault_injection.opt_in: "true"` annotation for
deployments you want to opt-in.

```
kind: Deployment
metadata:
  name: gke-ci
    annotations:
        fault_injection.opt_in: "true"
        fault_injection.max_to_delete: "3"
```

You can also specify `fault_injection.max_to_delete` if you want to support deleting
more than one pod for each run.

Please also make sure you specify a application label
in `spec/templates/metadata/labels/app/`, which is how
we'll discover the pods for a given deployment:

```
spec:
  replicas: 1
    template:
      metadata:
        labels:
          app: yourapp
```

You can do this for each deployment you want to be eligible.
Conversely, you can also use the `--include-by-default` CLI flag
which will default all deployments in except for those which specify
`fault_injection.opt_out: "true"` or which are excluded via parameter
passed to the `--ignore` flag which is a list of comma-separated namespaces
which are ignored (default value is `kube-system`).

Note that `opt_in` and `opt_out` are basically local overrides for global behavior:

    # include no matter what
    fault_injection.opt_in: "true"

    # exclude no matter what
    fault_injection.opt_out: "true"

Consequently, `opt_in: "false"` is *not* equivalent to `opt_out: "true"`.

Once you've opted in the appropriate deployments, then you just need to run `fi.py`.
The simplest approach is to run it locally, riding over `kubectl proxy`:

    # start kubectl in another terminal or in background
    kubectl proxy &

    # install and run
    git clone ...
    virtualenv env
    . ./env/bin/activate
    pip install -r requirements.txt
    python fi --loc http://localhost:8001

When you run it, you'll get output like this:

```
deployment: gke-ci
selected 1 of 1 pods: gke-ci-3385245117-fsj0t
        DELETE /api/v1/namespaces/default/pods/gke-ci-3385245117-fsj0t

deleted 1 out of 1 considered pods
```

You can also use the `Dockerfile` included in this repository
to run it as a Kubernetes Cron Job, where it'll use the container's
serviceaccount tokens to authenticate to `http://kubernetes`.


## Missing features.

There are a lot of other ideas worth exploring here!
A non-exhaustive list is:

1. We should do weighted random selection, preferring older pods (causing age of pods to converge over time).
2. We should support different kinds of operations beyond simply deleting pods.
3. We should have a backoff, such that if the youngest pod in a given deployment is younger than
    say 10 minutes (configurable!), we don't pile on things that are already failing.
