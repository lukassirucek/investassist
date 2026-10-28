#!/usr/bin/env python3
"""Mail event log (what the bank/broker/platform e-mails told us), shown on the dashboard.

  python3 -I scripts/mail_events.py add --date 2026-10-14 --source example_broker --kind rebalance --subject "..." --summary "..." [--action none|review|urgent] [--deadline YYYY-MM-DD]
  python3 -I scripts/mail_events.py list [--days 14]
  python3 -I scripts/mail_events.py last                  # newest event date per source (where the next mail search should start)

kind: trade | deposit | dividend | corporate_action | rebalance | statement | balance | savings_plan | terms_change | fee | newsletter_lead | security | other
One row per mail; duplicates (date + source + subject) are skipped. Never put account numbers or credentials here.
"""
import argparse, csv, datetime as dt, os, sys

P = 'data/ledger/mail_events.csv'
COLS = ['date', 'source', 'kind', 'subject', 'summary', 'action', 'deadline']


def rows():
    return list(csv.DictReader(open(P, encoding='utf-8'))) if os.path.exists(P) else []


def add(a):
    cur = rows()
    if any(r['date'] == a.date and r['source'] == a.source and r['subject'] == a.subject for r in cur):
        print('duplicate skipped'); return
    new = not os.path.exists(P)
    os.makedirs(os.path.dirname(P), exist_ok=True)
    with open(P, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        w.writerow(dict(date=a.date, source=a.source, kind=a.kind, subject=a.subject, summary=a.summary, action=a.action, deadline=a.deadline or ''))
    print('added')


def lst(days):
    cut = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    for r in sorted(rows(), key=lambda r: r['date'], reverse=True):
        if r['date'] >= cut:
            print(f"{r['date']} | {r['source']:12} | {r['kind']:16} | {r['action']:7} | {r['subject'][:50]} | {r['summary'][:90]}")


def last():
    d = {}
    for r in rows():
        d[r['source']] = max(d.get(r['source'], ''), r['date'])
    for k, v in sorted(d.items()):
        print(f'{k}: {v}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('add')
    for k in ('date', 'source', 'kind', 'subject', 'summary'):
        p.add_argument('--' + k, required=True)
    p.add_argument('--action', default='none', choices=['none', 'review', 'urgent']); p.add_argument('--deadline', default='')
    l = sp.add_parser('list'); l.add_argument('--days', type=int, default=14)
    sp.add_parser('last')
    a = ap.parse_args()
    {'add': lambda: add(a), 'list': lambda: lst(a.days), 'last': last}[a.cmd]()
