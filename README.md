# Oximeter Monitor Telegram Bot
Project made for my Microcontrollers class, the goal of this project is to collect the heartrate and oxygen saturation data using the ESP32 microcontroller
and the MAX30100 sensor. The whole project is divided into 3 parts/repositories: the [microcontroller firmware](https://github.com/LaBatata101/oximeter-esp32-firmware),
the [REST Api](https://github.com/LaBatata101/oximeter-rest-api) for the data management and the Telegram bot (this repository) for real time data visualization.

## Dependencies
- python-telegram-bot v20
- aiohttp v3.8.1

## Installing and running the project
Follow [this tutorial](https://core.telegram.org/bots) on how to create a Telegram Bot and get your Bot token.

Clone the project:
```bash
$ git clone https://github.com/LaBatata101/oximeter-telegram-bot
$ cd oximeter-telegram-bot/
```

Installing the dependencies using `pip`:
```bash
$ pip install -r requirements.txt
```
Or, using `poetry`:
```bash
$ poetry install
```

Running:
```bash
$ BOT_TOKEN=YOUR_BOT_TOKEN python oximeter/bot.py
```

Once you start a conversation with the bot type `/help` for the available commands.
