#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import socket, json, sys, time
from classes.round import Round
from urllib.request import urlopen
from functions import ConsoleColors as colors
from functions import get_data_from_api, Message


class Flags:
    db = None
    socket = None

    def __init__(self, db):
        self.db = db
        Message.success('Class is initializing')

        Message.info('Get data from api')
        data = get_data_from_api()
        
        try:
            lifetime = data["response"]["settings"]["flags"]["lifetime"]
            round_length = data["response"]["settings"]["round_length"]
        except Exception:
            Message.fail('Error with parse in response')
            sys.exit(0)

        self.life = lifetime * round_length

    def start(self):
        Message.success('Class is initialized. Starting')

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('0.0.0.0', 9090))
        self.socket.listen(1)

        while True:
            conn, address = self.socket.accept()
            print('connected:', address) # Возможно лишнее!!!
            process = multiprocessing.Process(target=self.recv, args=(conn, address))
            process.daemon = True
            process.start()

    def recv(self, connection, address):
        team = self.db.teams.find_one({'host': address[0]})
        
        if not bool(team):
            connection.send(('Who are you?\n Goodbye\n').encode())
            connection.close()    

        try:
            self.process_one_team(connection, team)
        except KeyboardInterrupt:
            print('ok, bye')
            self.socket.close()
            sys.exit(0)

    def process_one_team(self, connection, team):
        connection.send(('Welcome! \nYour team - ' + team["name"] + '\n').encode())

        try:
            while True:
                data = connection.recv(1024)
                data = str(data.rstrip().decode('utf-8'))

                flag = self.db.flags.find_one({'flag': data})
                if not bool(flag):
                    connection.send(('Flag is not found\n').encode())
                    continue

                if flag['team']['_id'] == team['_id']:
                    connection.send(('It`s your flag\n').encode())
                    continue

                self.life += flag["timestamp"]

                if self.life <= time.time():
                    connection.send(('This flag is too old\n').encode())
                    continue

                status = self.db.scoreboard.find_one({ 
                    'team._id': team['_id'],
                    'service._id': flag['service']['_id']
                })

                if status["status"] != 'UP':
                    connection.send(('Your service '+ flag['service']['name'] +' is not working\n').encode())
                    continue

                connection.send(('received\n').encode())
                # Добавляем очки

        except KeyboardInterrupt:
            print('ok, bye')
            self.socket.close()
            sys.exit(0)
            