#!/usr/bin/env python

"""
Venmo CLI.

Pay or charge people via the Venmo API:

    venmo pay @zackhsi 23.19 "Thanks for the beer <3"
    venmo charge 19495551234 23.19 "That beer wasn't free!"

Configure with:

    venmo configure
"""

import argparse
import os
import urllib
from datetime import datetime

from venmo import __version__, auth, settings, singletons, user

session = singletons.session()


def pay(args):
    _pay_or_charge(args)


def charge(args):
    args.amount = "-" + args.amount
    _pay_or_charge(args)


def _pay_or_charge(args):
    access_token = auth.get_access_token()
    if not access_token:
        return
    params = {
        'note': args.note,
        'amount': args.amount,
        'access_token': access_token,
        'audience': 'private',
    }
    if args.user.startswith("@"):
        user_id = user.id_from_username(args.user[1:])
        params['user_id'] = user_id
    else:
        params['phone'] = args.user
    response = session.post(
        _payments_url_with_params(params)
    ).json()
    _log_response(response)


def _payments_url_with_params(params):
    return "{payments_base_url}?{params}".format(
        payments_base_url=settings.PAYMENTS_URL,
        params=urllib.urlencode(params),
    )


def _log_response(response):
    if 'error' in response:
        message = response['error']['message']
        code = response['error']['code']
        print 'message="{}" code={}'.format(message, code)
        return

    payment = response['data']['payment']
    target = payment['target']

    payment_action = payment['action']
    if payment_action == 'charge':
        payment_action = 'charged'
    if payment_action == 'pay':
        payment_action = 'paid'

    amount = payment['amount']
    if target['type'] == 'user':
        user = "{first_name} {last_name}".format(
            first_name=target['user']['first_name'],
            last_name=target['user']['last_name'],
        )
    else:
        user = target[target['type']],
    note = payment['note']

    print 'Successfully {payment_action} {user} ${amount} for "{note}"'.format(
        payment_action=payment_action,
        user=user,
        amount=amount,
        note=note,
    )


def status(args):
    print "\n".join([_version(), _credentials()])


def _version():
    return "Version {}".format(__version__)


def _credentials():
    try:
        updated_at = os.path.getmtime(settings.CREDENTIALS_FILE)
        updated_at = datetime.fromtimestamp(updated_at)
        updated_at = updated_at.strftime("%Y-%m-%d %H:%M")
        return """Credentials (updated {updated_at}):
    User: {user}
    Token: {token}""".format(updated_at=updated_at,
                             user=auth.get_username(),
                             token=auth.get_access_token())
    except OSError:
        return "No credentials"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers()

    for action in ["pay", "charge"]:
        subparser = subparsers.add_parser(action)
        subparser.add_argument(
            "user",
            help="who to {}, either phone or username".format(action),
        )
        subparser.add_argument("amount", help="how much to pay or charge")
        subparser.add_argument("note", help="what the request is for")
        subparser.set_defaults(func=globals()[action])

    parser_configure = subparsers.add_parser('configure')
    parser_configure.set_defaults(func=auth.configure)

    parser_search = subparsers.add_parser('search')
    parser_search.add_argument("query", help="search query")
    parser_search.set_defaults(func=user.print_search)

    parser_status = subparsers.add_parser('status')
    parser_status.set_defaults(func=status)

    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s ' + __version__)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
