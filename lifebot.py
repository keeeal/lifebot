
import os, asyncio, json, argparse
from random import choices

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


def table(data: dict, cols=('TASK', 'WEIGHT')):
    keys, values = zip(*data.items())
    df = DataFrame({cols[0]: keys, cols[1]: values})
    return block(df.to_string(index=False))


def main(config_file):

    # load config file or create it
    if os.path.isfile(config_file):
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {'token': '', 'prefix': '-'}
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    # check for auth token
    if not config['token']:
        print('Error: Token not found.')
        print('Copy bot token into "{}"'.format(config_file))
        return

    # create client
    client = discord.Client()
    user_data = {}

    # define commands
    prefix = config['prefix'][0]
    parser = argparse.ArgumentParser(prefix_chars=prefix)
    parser.add_argument(2*prefix + 'edit', metavar='TASK', nargs='+',
        help='Add a new task or edit an existing one.')
    parser.add_argument(2*prefix + 'list', action='store_true',
        help='Display the current task list.')
    parser.add_argument(2*prefix + 'roll', action='store_true',
        help='Choose a task weighted by priority.')

    # format help messages
    usage_help = block(parser.format_help().replace(
        os.path.basename(__file__) + ' ', '', 1))
    no_tasks = 'Your task list is empty.'

    @client.event
    async def on_ready():
        print('Logged in as', client.user.name)

    @client.event
    async def on_message(m: discord.Message):
        if m.author == client.user:
            return

        # get commands from message
        if m.content.startswith(prefix):
            try:
                args = vars(parser.parse_args(m.content.split()))
            except SystemExit:
                await m.channel.send(usage_help)
                return

            # get user's data
            user_data[m.author] = user_data.get(m.author,
                {'tasks': {}, 'edit': None})
            data = user_data[m.author]
            data['tasks'] = clean(data['tasks'])

            # edit command
            if args['edit']:
                task = ' '.join(args['edit'])
                weight = data['tasks'].get(task, 1)
                embed = Embed(description=table(fib({task: weight})))
                reply = await m.channel.send(embed=embed)

                for emoji in '🔼', '🔽':
                    await reply.add_reaction(emoji)

                data['tasks'][task] = weight
                data['edit'] = reply, task

            # list command
            if args['list']:
                data['edit'] = None
                if data['tasks']:
                    embed = Embed(description=table(fib(data['tasks'])))
                    await m.channel.send(embed=embed)
                else:
                    embed = Embed(description=block(no_tasks))
                    await m.channel.send(embed=embed)

            # roll command
            if args['roll']:
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
    client.run(config['token'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', '-c', default='config.json')
    main(**vars(parser.parse_args()))
