
import os
from random import choices
from argparse import ArgumentParser
from configparser import ConfigParser

import discord
from discord import Embed
from pandas import DataFrame


def clean(data: dict):
    return {k: v for k, v in data.items() if 0 < v}


def fib(data: dict):
    def f(n, x=0, y=1):
        return x if n < 0 else f(n - 1, y, x + y)
    return {k: f(v) * bool(v) for k, v in data.items()}


def block(message):
    return '```' + message + '```'


def table(data: dict, cols=('TASK', 'PRIORITY')):
    keys = sorted(data, key=data.get, reverse=True)
    values = list(map(data.get, keys))
    df = DataFrame({cols[0]: keys, cols[1]: values})
    return block(df.to_string(index=False))


def main(config_file):

    # load config file or create it
    config = ConfigParser()
    if os.path.isfile(config_file):
        config.read(config_file)
    else:
        config.read_dict({'LIFEBOT': {'token': '', 'prefix': '--'}})
        with open(config_file, 'w') as f:
            config.write(f)

    # check for auth token
    if not config['LIFEBOT']['token']:
        print('Error: Token not found.')
        print('Copy bot token into "{}"'.format(config_file))
        return

    # TODO: load data here
    user_data = {}

    # define bot commands
    prefix = config['LIFEBOT']['prefix']
    commands = ArgumentParser(prefix_chars=prefix)
    commands.add_argument(prefix + 'edit', metavar='TASK', nargs='+',
        help='Add a new task or edit an existing one.')
    commands.add_argument(prefix + 'list', action='store_true',
        help='Display the current task list.')
    commands.add_argument(prefix + 'roll', action='store_true',
        help='Choose a task weighted by priority.')

    # format help messages
    no_tasks = 'Your task list is empty.'
    usage_help = block(commands.format_help().replace(
        os.path.basename(__file__) + ' ', '', 1))

    # create client
    client = discord.Client()

    @client.event
    async def on_ready():
        print('Logged in as', client.user.name)

    @client.event
    async def on_message(m: discord.Message):
        if m.author == client.user:
            return

        # get command from message
        if m.content.startswith(prefix):
            try:
                command = vars(commands.parse_args(m.content.split()))
            except SystemExit:
                await m.channel.send(usage_help)
                return

            # get user's data
            user_data[m.author] = user_data.get(m.author,
                {'tasks': {}, 'edit': None})
            data = user_data[m.author]
            data['tasks'] = clean(data['tasks'])

            # edit command
            if command['edit']:
                task = ' '.join(command['edit'])
                weight = data['tasks'].get(task, 1)
                embed = Embed(description=table(fib({task: weight})))
                reply = await m.channel.send(embed=embed)

                for emoji in '🔼', '🔽':
                    await reply.add_reaction(emoji)

                data['tasks'][task] = weight
                data['edit'] = reply, task

            # list command
            if command['list']:
                data['edit'] = None
                if data['tasks']:
                    embed = Embed(description=table(fib(data['tasks'])))
                    await m.channel.send(embed=embed)
                else:
                    embed = Embed(description=block(no_tasks))
                    await m.channel.send(embed=embed)

            # roll command
            if command['roll']:
                data['edit'] = None
                if data['tasks']:
                    task = choices(*zip(*fib(data['tasks']).items()))[0]
                    embed = Embed(description=block(task))
                    await m.channel.send(embed=embed)
                else:
                    embed = Embed(description=block(no_tasks))
                    await m.channel.send(embed=embed)

    @client.event
    async def on_reaction_add(r: discord.Reaction, u: discord.User):
        if u not in user_data:
            return

        # get user data
        data = user_data[u]
        if not data['edit']:
            return

        # get editable task
        reply, task = data['edit']
        if r.message.id == reply.id:
            weight = data['tasks'][task]

            if r.emoji == '🔼':
                data['tasks'][task] = min(weight + 1, 100)
            elif r.emoji == '🔽':
                data['tasks'][task] = max(weight - 1, 0)

            weight = data['tasks'][task]
            embed = Embed(description=table(fib({task: weight})))
            await r.message.edit(embed=embed)

    # start bot
    client.run(config['LIFEBOT']['token'])


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--config-file', '-c', default='config.ini')
    main(**vars(parser.parse_args()))
