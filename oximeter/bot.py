import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp
import pytz
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters)

BASE_URL = "https://oximeter-api.herokuapp.com"


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_to_dict(items: list[tuple[Any, Any]]):
    d: dict[str, list] = {}
    for item_a, item_b in items:
        d.setdefault(item_a, []).append(item_b)
    return d


def dict_avg(d: dict[str, list[int]]):
    for key, values in d.items():
        d.update({key: sum(values) // len(values)})
    return d


async def fetch_sensor_data(context: ContextTypes.DEFAULT_TYPE):
    job = context.job

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/sensor/last/") as response:
            data = await response.json()
            date = datetime.strptime(data["date"], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=pytz.timezone("America/Fortaleza")
            )
            date_now = datetime.now().replace(tzinfo=pytz.timezone("America/Fortaleza"))
            time_diff = (date_now - date).seconds
            print(f"{date_now=}\n{date=}")
            print(f"{date_now.strftime('%Y-%m-%dT%H:%M:%S')=}\n{date.strftime('%Y-%m-%dT%H:%M:%S')=}\n{time_diff=}")
            if 0 < time_diff <= 7:
                await context.bot.send_message(job.chat_id, f"❤️ {data['bpm']} bpm\n🫁 {data['spo2']}% SpO2")
            else:
                await context.bot.send_message(job.chat_id, "Nenhum dado recente foi recebido do oxímetro!")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False

    for job in current_jobs:
        job.schedule_removal()
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Olá! Digite /help para mostrar os comandos possíveis."
    )


async def unkown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Comando desconhecido!")


async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_repeating(fetch_sensor_data, 1, chat_id=chat_id, name=str(chat_id))


async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    if not job_removed:
        await update.message.reply_text("Nenhum monitoramento foi iniciado.")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="""
Comandos disponíveis:
/start \\- inicia a conversa com o bot
/help \\- mostra essa mensagem
/monitorar \\- começa a receber dados do oxímetro
/parar \\- para de receber dados do oxímetro
/grafico *_tipo_* *_data_* \\- mostra um gráfico com os dados do sensor para uma certa data
        \\- *_tipo_* pode ser: _ __dia__ _, _ __mes__ _ ou _ __ano__ _
        \\- *_data_* tem que estar no formato:
            \\- *dd/mm/yyyy* se o *_tipo_* escolhido for _dia_
            \\- *mm/yyyy* se o *_tipo_* escolhido for _mes_
            \\- *yyyy* se o *_tipo_* escolhido for _ano_
        """,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def parse_arguments(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> Optional[tuple[dict[str, int], str]]:
    if len(context.args) < 2:
        await context.bot.send_message(chat_id=chat_id, text="Numero de argumentos incorretos. Digite /help")
        return None

    date_type = context.args[0]  # can be "dia", "mes" or "ano"
    date_format = ""
    date = {}
    try:
        match date_type:
            case "dia":
                date_format = "dd/mm/yyyy"
                _datetime = datetime.strptime(context.args[1], "%d/%m/%Y")
                date.update({"day": _datetime.day, "month": _datetime.month, "year": _datetime.year})
            case "mes":
                date_format = "mm/yyyy"
                _datetime = datetime.strptime(context.args[1], "%m/%Y")
                date.update({"month": _datetime.month, "year": _datetime.year})
            case "ano":
                date_format = "yyyy"
                _datetime = datetime.strptime(context.args[1], "%Y")
                date.update({"year": _datetime.year})
            case _:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"""
    Opção desconhecida *{date_type}*\\.
    Opções disponíveis: *dia*, *mes* ou *ano*\\.
    """,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Data *{context.args[1]}* não está no formato *{date_format}*",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return None

    return date, date_type


async def show_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = await parse_arguments(update.effective_chat.id, context)
    if date is None:
        return

    date, date_type = date[0], date[1]

    bpm = []
    spo2 = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/sensor/date/", params=date) as response:
            if response.status == 404:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text="Nenhum dado encontrado para essa data!"
                )
                return

            data_samples = await response.json()
            for data_sample in data_samples:
                date_str = datetime.strptime(data_sample["date"], "%Y-%m-%dT%H:%M:%S")

                if date_type == "dia":
                    date_str = date_str.strftime("%H:%M:%S")
                elif date_type == "mes":
                    date_str = date_str.strftime("%d/%m/%Y")
                elif date_type == "ano":
                    date_str = date_str.strftime("%m/%Y")

                bpm.append((date_str, data_sample["bpm"]))
                spo2.append((date_str, data_sample["spo2"]))

        bpm = dict_avg(convert_to_dict(bpm))
        spo2 = dict_avg(convert_to_dict(spo2))

        async with session.post(
            "https://quickchart.io/chart",
            json={
                "backgroundColor": "#fff",
                "width": 500,
                "height": 300,
                "devicePixelRatio": 1.5,
                "chart": {
                    "type": "line",
                    "data": {
                        "labels": list(bpm),
                        "datasets": [
                            {
                                "label": "BPM",
                                "backgroundColor": "#eb3639",
                                "borderColor": "#eb3639",
                                "fill": False,
                                "data": list(bpm.values()),
                            },
                            {
                                "label": "SpO2",
                                "backgroundColor": "#0f58b8",
                                "borderColor": "#0f58b8",
                                "fill": False,
                                "data": list(spo2.values()),
                            },
                        ],
                    },
                },
            },
        ) as response:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
            data = await response.read()

            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=data)


if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if token is None:
        print("BOT_TOKEN not set")
        exit(1)

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("monitorar", start_monitoring))
    app.add_handler(CommandHandler("parar", stop_monitoring))
    app.add_handler(CommandHandler("grafico", show_chart))
    app.add_handler(MessageHandler(filters.COMMAND, unkown_cmd))

    app.run_polling()
