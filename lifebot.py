
import os, asyncio, argparse, json
from random import choices
from itertools import reduce

import discord


def fib(n, x=0, y=1):
    return x if n < 0 else fib(n-1, y, x+y)


def table(data, key_name='TASK', value_name='WEIGHT'):
    import pandas as pd
    keys, values = zip(*data.items())
    df = pd.DataFrame({key_name: keys, value_name: values})
    return '```' + df.to_string(index=False) + '```'


def main(config_file):

    # load config file or create it
    if os.path.isfile(config_file):
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {'token': ''}
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    # check for auth token
    if not config['token']:
        print('Error: Token not found.')
        print('Copy bot token into "{}"'.format(config_file))
        return


    # create client
    client = discord.Client()
    data = {}

    # define commands
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--roll', action='store_true')
    parser.add_argument('--add', metavar='TASK')
    parser.add_argument('--delete', metavar='TASK')

    # format help message
    usage_help = parser.format_help().replace(
        os.path.basename(__file__) + ' ', '')


    @client.event
    async def on_ready():
        print('Logged in as', client.user.name)


    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        content, channel = message.content, message.channel
        if content.startswith('-'):
            try:
                args = vars(parser.parse_args(content.split()))

                if args['list']:
                    embed = discord.Embed(description=table(data))
                    await channel.send(embed=embed)

                if args['roll']:
                    task = choices(*zip(*data.items()))[0]
                    embed = discord.Embed(description='TASK: zz' + task)
                    await channel.send(embed=embed)

                if args['add']:
                    data[args['add']] = data.get(args['add'], 0) + 1
                    embed = discord.Embed(
                        description=table({args['add']: data[args['add']]}))
                    await channel.send(embed=embed)

                if args['delete']:
                    del data[args['delete']]
                    embed = discord.Embed(
                        description=args['delete'] + ' DELETED')
                    await channel.send(embed=embed)

            except SystemExit:
                await channel.send(usage_help)


    # start bot
    client.run(config['token'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', '-c', default='config.json')
    main(**vars(parser.parse_args()))