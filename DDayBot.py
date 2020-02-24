# -*- coding: utf-8 -*-
import asyncio
import inspect
import json
import os
import ssl
from datetime import datetime

import certifi
import websockets

from Event import Event

json_file_name = "jsonData.json"


def ToJson(obj):
    return json.dumps(obj, default=lambda x: x.isoformat(' ', 'seconds') if type(x) == datetime else x.__dict__,
                      sort_keys=True, indent=4)


# noinspection PyPep8Naming,NonAsciiCharacters
class DDayBot:
    def __init__(self, slack):

        self.command_dict = {function_name: getattr(DDayBot, function_name) for function_name in dir(self)
                             if callable(getattr(DDayBot, function_name)) and not function_name.startswith("_")}
        self.parameter_dict = {name: [i for i in inspect.signature(function).parameters.keys() if i not in ["self"]] for
                               name, function in self.command_dict.items()}
        self.help_dict = {function_name: f"!{function_name}{''.join([' ' + i for i in args])}" for function_name, args
                          in self.parameter_dict.items()}
        self.slack = slack

        self._load_from_file()

    async def _listen(self):
        ssl_context = ssl.create_default_context()
        ssl_context.load_verify_locations(certifi.where())

        response = self.slack.rtm.start()
        url = response.body['url']
        socket = await websockets.connect(url, ssl=ssl_context)

        prev_day = -1

        while True:
            await asyncio.sleep(0.1)

            if prev_day != datetime.now().day and datetime.now().hour == 9 and channel:
                self.slack.chat.post_message(channel, self.목록())
                prev_day = datetime.now().day

            json_message = json.loads(await socket.recv())
            channel = ""
            try:
                if json_message.get("type") == "message":
                    message = json_message.get("text")
                    channel = json_message.get("channel")

                    if message:
                        response = self._run(message)
            except TypeError as type_error:
                error_message = str(type_error)
                if "positional" in error_message:
                    response = "명령어의 인자 갯수가 맞지 않습니다. 띄어쓰기는 _ 로 대신 사용해주세요."
                elif "int()":
                    response = "날짜는 숫자로만 입력해주세요."

            except Exception as e:
                response = "error: " + str(e)

            if response and channel:
                self.slack.chat.post_message(channel, response)

    def _run(self, command):
        if not command.startswith("!"):
            return
        command, *params = command[1:].split(" ")
        for i in range(len(params)):
            params[i] = params[i].replace("\"", "").replace("\'", "").replace("_", " ")

        if command not in self.command_dict:
            return "잘못된 명령어 입니다. \"!명령어\"를 입력하시면 명령어 목록을 표시합니다."

        return self.command_dict[command](self, *params)

    def _write_to_file(self):
        with open(json_file_name, "w+") as file:
            file.write(ToJson(self.events))
            file.truncate()

    def _load_from_file(self):
        if os.path.exists(json_file_name):
            with open(json_file_name, "r") as file:
                contents = file.read()
                if contents:
                    json_value = json.loads(contents)
                    self.events = Event.fromJson(json_value)
                else:
                    self.events = []

    def 명령어(self):
        return "\n".join(["명령어 목록"] + list(self.help_dict.values()))

    def 등록(self, 이벤트이름, 년, 월, 일, 시=0, 분=0):
        if int(년) < 100:
            년 = int(년) + 2000

        self.삭제(이벤트이름)
        self.events.append(Event(이벤트이름, datetime(int(년), int(월), int(일), int(시), int(분))))
        self._write_to_file()
        return f"{이벤트이름}이 등록되었습니다."

    def 목록(self):
        event_strings = []

        events = sorted(self.events, key=lambda x: x.date)

        for event in events:
            format_name = event.name
            format_name = event.name + " "*((15 - len(format_name))*3) + " " * (format_name.count(" ")*2)
            event_strings.append(f"{format_name} {event.date.isoformat(' ', 'seconds')} D-{event.remainDayFromNow()}")

        if len(event_strings) == 0:
            return "이벤트가 없습니다."

        return "\n".join(event_strings)

    def 삭제(self, 이벤트이름):
        for event in self.events:
            if event.name == 이벤트이름:
                self.events.remove(event)
                break
        return f"{이벤트이름}이 삭제되었습니다."
