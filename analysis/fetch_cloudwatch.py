import argparse
import csv
import datetime as dt
import boto3

p = argparse.ArgumentParser()
p.add_argument('--asg', required=True)
p.add_argument('--lb', default='')
p.add_argument('--tg', default='')
p.add_argument('--start', required=True, help='UTC, like 2026-11-10T09:00:00')
p.add_argument('--end', required=True, help='UTC, like 2026-11-10T10:00:00')
p.add_argument('--region', default='ap-south-1')
p.add_argument('--out', default='cw.csv')
a = p.parse_args()

utc = dt.timezone.utc
start = dt.datetime.fromisoformat(a.start).replace(tzinfo=utc)
end = dt.datetime.fromisoformat(a.end).replace(tzinfo=utc)

cw = boto3.client('cloudwatch', region_name=a.region)
asg_dim = [{'Name': 'AutoScalingGroupName', 'Value': a.asg}]

def q(qid, ns, name, dims, stat):
    return {
        'Id': qid,
        'MetricStat': {
            'Metric': {'Namespace': ns, 'MetricName': name, 'Dimensions': dims},
            'Period': 60,
            'Stat': stat,
        },
        'ReturnData': True,
    }

queries = [
    q('in_service', 'AWS/AutoScaling', 'GroupInServiceInstances', asg_dim, 'Average'),
    q('desired', 'AWS/AutoScaling', 'GroupDesiredCapacity', asg_dim, 'Average'),
    q('cpu', 'AWS/EC2', 'CPUUtilization', asg_dim, 'Average'),
]

if a.lb and a.tg:
    alb_dim = [
        {'Name': 'TargetGroup', 'Value': a.tg},
        {'Name': 'LoadBalancer', 'Value': a.lb},
    ]
    queries += [
        q('healthy_hosts', 'AWS/ApplicationELB', 'HealthyHostCount', alb_dim, 'Average'),
        q('alb_p95_s', 'AWS/ApplicationELB', 'TargetResponseTime', alb_dim, 'p95'),
        q('req_count', 'AWS/ApplicationELB', 'RequestCount', alb_dim, 'Sum'),
    ]

rows = {}
token = None
while True:
    kw = dict(MetricDataQueries=queries, StartTime=start, EndTime=end, ScanBy='TimestampAscending')
    if token:
        kw['NextToken'] = token
    resp = cw.get_metric_data(**kw)
    for r in resp['MetricDataResults']:
        for t, v in zip(r['Timestamps'], r['Values']):
            rows.setdefault(int(t.timestamp()), {})[r['Id']] = v
    token = resp.get('NextToken')
    if not token:
        break

cols = ['in_service', 'desired', 'cpu', 'healthy_hosts', 'alb_p95_s', 'req_count']
with open(a.out, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['epoch'] + cols)
    for epoch in sorted(rows):
        w.writerow([epoch] + [rows[epoch].get(c, '') for c in cols])

print('wrote', a.out, 'with', len(rows), 'rows')