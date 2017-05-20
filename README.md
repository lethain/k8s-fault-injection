


There are a handful of ways to configure which deployments are eligible for fault injection.
The recommended starting place is to add the `fault_injection.opt_in: "true"` annotation for
deployments you want to opt-in.

```
kind: Deployment
metadata:
  name: gke-ci
    annotations:
        fault_injection.opt_in: "true"
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

You can also use the `Dockerfile` included in this repository
to run it as a Kubernetes Cron Job, where it'll use the container's
serviceaccount tokens to authenticate to `http://kubernetes`.
