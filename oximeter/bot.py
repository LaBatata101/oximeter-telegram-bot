import logging
import os
from datetime import datetime

import aiohttp
from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters)

BASE_URL = "https://oximeter-api.herokuapp.com"


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


async def fetch_sensor_data(context: ContextTypes.DEFAULT_TYPE):
    job = context.job

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/sensor/last/") as response:
            data = await response.json()
            date = datetime.strptime(data["date"], "%Y-%m-%dT%H:%M:%S")
            time_diff = (datetime.now() - date).total_seconds()
            print(f"{time_diff=}")
            if 0 < time_diff <= 5:
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
/start - inicia a conversa com o bot
/help - mostra essa mensagem
/monitorar - começa a receber dados do oxímetro
/parar - para de receber dados do oxímetro
        """,
    )


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
    app.add_handler(MessageHandler(filters.COMMAND, unkown_cmd))

    app.run_polling()
