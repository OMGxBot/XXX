from time import time, monotonic
from datetime import datetime
from sys import executable
from os import execl as osexecl
from asyncio import create_subprocess_exec, gather
from uuid import uuid4
from base64 import b64decode

from requests import get as rget
from psutil import (boot_time, cpu_count, cpu_percent, cpu_freq, disk_usage, net_io_counters, swap_memory, virtual_memory)
from pytz import timezone
from bs4 import BeautifulSoup
from signal import signal, SIGINT
from aiofiles.os import path as aiopath, remove as aioremove
from aiofiles import open as aiopen
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, private, regex
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, bot_cache, bot_name, config_dict, user_data, botStartTime, LOGGER, Interval, DATABASE_URL, QbInterval, INCOMPLETE_TASK_NOTIFIER, scheduler
from bot.version import get_version
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.bot_utils import get_readable_time, cmd_exec, sync_to_async, new_task, set_commands, update_user_ldata, get_readable_file_size, get_progress_bar_string
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, editMessage, editReplyMarkup, sendFile, deleteMessage, delete_all_messages
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.listeners.aria2_listener import start_aria2_listener
from .helper.themes import BotTheme
from .modules import authorize, clone, gd_count, gd_delete, gd_list, cancel_mirror, mirror_leech, status, torrent_search, torrent_select, ytdlp, \
                     rss, shell, eval, users_settings, bot_settings, speedtest, save_msg, images, imdb, anilist, mediainfo, mydramalist, gen_pyro_sess, \
                     gd_clean, broadcast, category_select

async def stats(_, message, edit_mode=False):
    buttons = ButtonMaker()
    sysTime     = get_readable_time(time() - boot_time())
    botTime     = get_readable_time(time() - botStartTime)
    total, used, free, disk = disk_usage('/')
    total       = get_readable_file_size(total)
    used        = get_readable_file_size(used)
    free        = get_readable_file_size(free)
    sent        = get_readable_file_size(net_io_counters().bytes_sent)
    recv        = get_readable_file_size(net_io_counters().bytes_recv)
    tb          = get_readable_file_size(net_io_counters().bytes_sent + net_io_counters().bytes_recv)
    cpuUsage    = cpu_percent(interval=0.1)
    v_core      = cpu_count(logical=True) - cpu_count(logical=False)
    memory      = virtual_memory()
    mem_p       = memory.percent
    swap        = swap_memory()

    bot_stats = f'<b><i><u>Bot Statistics</u></i></b>\n\n'\
                f'<code>CPU  : {get_progress_bar_string(cpuUsage)}</code> {cpuUsage}%\n' \
                f'<code>RAM  : {get_progress_bar_string(mem_p)}</code> {mem_p}%\n' \
                f'<code>SWAP : {get_progress_bar_string(swap.percent)}</code> {swap.percent}%\n' \
                f'<code>DISK : {get_progress_bar_string(disk)}</code> {disk}%\n\n' \
                f'<code>Bot Uptime      : </code> {botTime}\n' \
                f'<code>Uploaded        : </code> {sent}\n' \
                f'<code>Downloaded      : </code> {recv}\n' \
                f'<code>Total Bandwidth : </code> {tb}'

    sys_stats = f'<b><i><u>System Statistics</u></i></b>\n\n'\
                f'<b>System Uptime:</b> <code>{sysTime}</code>\n' \
                f'<b>CPU:</b> {get_progress_bar_string(cpuUsage)}<code> {cpuUsage}%</code>\n' \
                f'<b>CPU Total Core(s):</b> <code>{cpu_count(logical=True)}</code>\n' \
                f'<b>P-Core(s):</b> <code>{cpu_count(logical=False)}</code> | ' \
                f'<b>V-Core(s):</b> <code>{v_core}</code>\n' \
                f'<b>Frequency:</b> <code>{cpu_freq(percpu=False).current / 1000:.2f} GHz</code>\n\n' \
                f'<b>RAM:</b> {get_progress_bar_string(mem_p)}<code> {mem_p}%</code>\n' \
                f'<b>Total:</b> <code>{get_readable_file_size(memory.total)}</code> | ' \
                f'<b>Free:</b> <code>{get_readable_file_size(memory.available)}</code>\n\n' \
                f'<b>SWAP:</b> {get_progress_bar_string(swap.percent)}<code> {swap.percent}%</code>\n' \
                f'<b>Total</b> <code>{get_readable_file_size(swap.total)}</code> | ' \
                f'<b>Free:</b> <code>{get_readable_file_size(swap.free)}</code>\n\n' \
                f'<b>DISK:</b> {get_progress_bar_string(disk)}<code> {disk}%</code>\n' \
                f'<b>Total:</b> <code>{total}</code> | <b>Free:</b> <code>{free}</code>'

    buttons.ibutton("Sys Stats",  "show_sys_stats")
    buttons.ibutton("Repo Stats", "show_repo_stats")
    buttons.ibutton("Bot Limits", "show_bot_limits")
    buttons.ibutton("Close", "close_signal")
    sbtns = buttons.build_menu(2)
    if not edit_mode:
        await message.reply(bot_stats, reply_markup=sbtns)
    return bot_stats, sys_stats


async def send_bot_stats(_, query):
    buttons = ButtonMaker()
    bot_stats, _ = await stats(_, query.message, edit_mode=True)
    buttons.ibutton("Sys Stats",  "show_sys_stats")
    buttons.ibutton("Repo Stats", "show_repo_stats")
    buttons.ibutton("Bot Limits", "show_bot_limits")
    buttons.ibutton("Close",      "close_signal")
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(bot_stats, reply_markup=sbtns)


async def send_sys_stats(_, query):
    buttons = ButtonMaker()
    _, sys_stats = await stats(_, query.message, edit_mode=True)
    buttons.ibutton("Bot Stats",  "show_bot_stats")
    buttons.ibutton("Repo Stats", "show_repo_stats")
    buttons.ibutton("Bot Limits", "show_bot_limits")
    buttons.ibutton("Close",      "close_signal")
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(sys_stats, reply_markup=sbtns)


async def send_repo_stats(_, query):
    buttons = ButtonMaker()
    if await aiopath.exists('.git'):
        last_commit = (await cmd_exec("git log -1 --date=short --pretty=format:'%cr'", True))[0]
        version     = (await cmd_exec("git describe --abbrev=0 --tags", True))[0]
        change_log  = (await cmd_exec("git log -1 --pretty=format:'%s'", True))[0]
    else:
        last_commit = 'No UPSTREAM_REPO'
        version     = 'N/A'
        change_log  = 'N/A'

    repo_stats = f'<b><i><u>Repo Info</u></i></b>\n\n' \
                  f'<code>Updated   : </code> {last_commit}\n' \
                  f'<code>Version   : </code> {version}\n' \
                  f'<code>Changelog : </code> {change_log}'

    buttons.ibutton("Bot Stats",  "show_bot_stats")
    buttons.ibutton("Sys Stats",  "show_sys_stats")
    buttons.ibutton("Bot Limits", "show_bot_limits")
    buttons.ibutton("Close", "close_signal")
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(repo_stats, reply_markup=sbtns)


async def send_bot_limits(_, query):
    buttons = ButtonMaker()
    DIR = 'Unlimited' if config_dict['DIRECT_LIMIT']    == '' else config_dict['DIRECT_LIMIT']
    YTD = 'Unlimited' if config_dict['YTDLP_LIMIT']     == '' else config_dict['YTDLP_LIMIT']
    GDL = 'Unlimited' if config_dict['GDRIVE_LIMIT']    == '' else config_dict['GDRIVE_LIMIT']
    TOR = 'Unlimited' if config_dict['TORRENT_LIMIT']   == '' else config_dict['TORRENT_LIMIT']
    CLL = 'Unlimited' if config_dict['CLONE_LIMIT']     == '' else config_dict['CLONE_LIMIT']
    MGA = 'Unlimited' if config_dict['MEGA_LIMIT']      == '' else config_dict['MEGA_LIMIT']
    TGL = 'Unlimited' if config_dict['LEECH_LIMIT']     == '' else config_dict['LEECH_LIMIT']
    UMT = 'Unlimited' if config_dict['USER_MAX_TASKS']  == '' else config_dict['USER_MAX_TASKS']
    BMT = 'Unlimited' if config_dict['QUEUE_ALL']       == '' else config_dict['QUEUE_ALL']

    bot_limit = f'<b><i><u>Zee Bot Limitations</u></i></b>\n' \
                f'<code>Torrent   : {TOR}</code> <b>GB</b>\n' \
                f'<code>G-Drive   : {GDL}</code> <b>GB</b>\n' \
                f'<code>Yt-Dlp    : {YTD}</code> <b>GB</b>\n' \
                f'<code>Direct    : {DIR}</code> <b>GB</b>\n' \
                f'<code>Clone     : {CLL}</code> <b>GB</b>\n' \
                f'<code>Leech     : {TGL}</code> <b>GB</b>\n' \
                f'<code>MEGA      : {MGA}</code> <b>GB</b>\n\n' \
                f'<code>User Tasks: {UMT}</code>\n' \
                f'<code>Bot Tasks : {BMT}</code>'

    buttons.ibutton("Bot Stats",  "show_bot_stats")
    buttons.ibutton("Sys Stats",  "show_sys_stats")
    buttons.ibutton("Repo Stats", "show_repo_stats")
    buttons.ibutton("Close", "close_signal")
    sbtns = buttons.build_menu(2)
    await query.answer()
    await query.message.edit_text(bot_limit, reply_markup=sbtns)


async def send_close_signal(_, query):
    await query.answer()
    try:
        await query.message.reply_to_message.delete()
    except Exception as e:
        LOGGER.error(e)
    await query.message.delete()



@new_task
async def start(client, message):
    buttons = ButtonMaker()
    buttons.ubutton(BotTheme('ST_BN1_NAME'), BotTheme('ST_BN1_URL'))
    buttons.ubutton(BotTheme('ST_BN2_NAME'), BotTheme('ST_BN2_URL'))
    reply_markup = buttons.build_menu(2)
    if len(message.command) > 1 and message.command[1] == "wzmlx":
        await deleteMessage(message)
    elif len(message.command) > 1 and config_dict['TOKEN_TIMEOUT']:
        userid = message.from_user.id
        encrypted_url = message.command[1]
        input_token, pre_uid = (b64decode(encrypted_url.encode()).decode()).split('&&')
        if int(pre_uid) != userid:
            return await sendMessage(message, '<b>Temporary Token is not yours!</b>\n\n<i>Kindly generate your own.</i>')
        data = user_data.get(userid, {})
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, '<b>Temporary Token already used!</b>\n\n<i>Kindly generate a new one.</i>')
        elif config_dict['LOGIN_PASS'] is not None and data['token'] == config_dict['LOGIN_PASS']:
            return await sendMessage(message, '<b>Bot Already Logged In via Password</b>\n\n<i>No Need to Accept Temp Tokens.</i>')
        buttons.ibutton('Activate Temporary Token', f'pass {input_token}', 'header')
        reply_markup = buttons.build_menu(2)
        msg = '<b><u>Generated Temporary Login Token!</u></b>\n\n'
        msg += f'<b>Temp Token:</b> <code>{input_token}</code>\n\n'
        msg += f'<b>Validity:</b> {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]))}'
        return await sendMessage(message, msg, reply_markup)
    elif await CustomFilters.authorized(client, message):
        start_string = BotTheme('ST_MSG', help_command=f"/{BotCommands.HelpCommand}")
        await sendMessage(message, start_string, reply_markup, photo=BotTheme('PIC'))
    elif config_dict['BOT_PM']:
        await sendMessage(message, BotTheme('ST_BOTPM'), reply_markup, photo=BotTheme('PIC'))
    else:
        await sendMessage(message, BotTheme('ST_UNAUTH'), reply_markup, photo=BotTheme('PIC'))
    await DbManger().update_pm_users(message.from_user.id)


async def token_callback(_, query):
    user_id = query.from_user.id
    input_token = query.data.split()[1]
    data = user_data.get(user_id, {})
    if 'token' not in data or data['token'] != input_token:
        return await query.answer('Already Used, Generate New One', show_alert=True)
    update_user_ldata(user_id, 'token', str(uuid4()))
    update_user_ldata(user_id, 'time', time())
    await query.answer('Activated Temporary Token!', show_alert=True)
    kb = query.message.reply_markup.inline_keyboard[1:]
    kb.insert(0, [InlineKeyboardButton('✅️ Activated ✅', callback_data='pass activated')])
    await editReplyMarkup(query.message, InlineKeyboardMarkup(kb))


async def login(_, message):
    if config_dict['LOGIN_PASS'] is None:
        return
    elif len(message.command) > 1:
        user_id = message.from_user.id
        input_pass = message.command[1]
        if user_data.get(user_id, {}).get('token', '') == config_dict['LOGIN_PASS']:
            return await sendMessage(message, '<b>Already Bot Login In!</b>')
        if input_pass == config_dict['LOGIN_PASS']:
            update_user_ldata(user_id, 'token', config_dict['LOGIN_PASS'])
            return await sendMessage(message, '<b>Bot Permanent Login Successfully!</b>')
        else:
            return await sendMessage(message, '<b>Invalid Password!</b>\n\nKindly put the correct Password .')
    else:
        await sendMessage(message, '<b>Bot Login Usage :</b>\n\n<code>/cmd {password}</code>')


async def restart(client, message):
    restart_message = await sendMessage(message, BotTheme('RESTARTING'))
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await delete_all_messages()
    for interval in [QbInterval, Interval]:
        if interval:
            interval[0].cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec('pkill', '-9', '-f', f'gunicorn|{bot_cache["pkgs"][-1]}')
    proc2 = await create_subprocess_exec('python3', 'update.py')
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(_, message):
    start_time = monotonic()
    reply = await sendMessage(message, BotTheme('PING'))
    end_time = monotonic()
    await editMessage(reply, BotTheme('PING_VALUE', value=int((end_time - start_time) * 1000)))


async def log(_, message):
    buttons = ButtonMaker()
    buttons.ibutton('📑 Log Display', f'wzmlx {message.from_user.id} logdisplay')
    buttons.ibutton('📨 Web Paste', f'wzmlx {message.from_user.id} webpaste')
    await sendFile(message, 'log.txt', buttons=buttons.build_menu(1))


async def search_images():
    if query_list := config_dict['IMG_SEARCH']:
        try:
            total_pages = config_dict['IMG_PAGE']
            base_url = "https://www.wallpaperflare.com/search"
            for query in query_list:
                query = query.strip().replace(" ", "+")
                for page in range(1, total_pages + 1):
                    url = f"{base_url}?wallpaper={query}&width=1280&height=720&page={page}"
                    r = rget(url)
                    soup = BeautifulSoup(r.text, "html.parser")
                    images = soup.select('img[data-src^="https://c4.wallpaperflare.com/wallpaper"]')
                    if len(images) == 0:
                        LOGGER.info("Maybe Site is Blocked on your Server, Add Images Manually !!")
                    for img in images:
                        img_url = img['data-src']
                        if img_url not in config_dict['IMAGES']:
                            config_dict['IMAGES'].append(img_url)
            if len(config_dict['IMAGES']) != 0:
                config_dict['STATUS_LIMIT'] = 2
            if DATABASE_URL:
                await DbManger().update_config({'IMAGES': config_dict['IMAGES'], 'STATUS_LIMIT': config_dict['STATUS_LIMIT']})
        except Exception as e:
            LOGGER.error(f"An error occurred: {e}")


async def bot_help(client, message):
    buttons = ButtonMaker()
    user_id = message.from_user.id
    buttons.ibutton('Basic', f'wzmlx {user_id} guide basic')
    buttons.ibutton('Users', f'wzmlx {user_id} guide users')
    buttons.ibutton('Mics', f'wzmlx {user_id} guide miscs')
    buttons.ibutton('Owner & Sudos', f'wzmlx {user_id} guide admin')
    buttons.ibutton('Close', f'wzmlx {user_id} close')
    await sendMessage(message, "㊂ <b><i>Help Guide Menu!</i></b>\n\n<b>NOTE: <i>Click on any CMD to see more minor detalis.</i></b>", buttons.build_menu(2))


async def restart_notification():
    now=datetime.now(timezone(config_dict['TIMEZONE']))
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith("⌬ <b><i>Restarted Successfully!</i></b>"):
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=msg)
                await aioremove(".restartmsg")
            else:
                await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True, disable_notification=True)
        except Exception as e:
            LOGGER.error(e)

    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y'), timz=config_dict['TIMEZONE'], version=get_version()) if cid == chat_id else BotTheme('RESTARTED')
                msg += "\n\n⌬ <b><i>Incomplete Tasks!</i></b>"
                for tag, links in data.items():
                    msg += f"\n➲ {tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg)

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y'), timz=config_dict['TIMEZONE'], version=get_version()))
        except Exception as e:
            LOGGER.error(e)
        await aioremove(".restartmsg")


async def main():
    await gather(start_cleanup(), torrent_search.initiate_search_tools(), restart_notification(), search_images(), set_commands(bot))
    await sync_to_async(start_aria2_listener, wait=False)
    
    bot.add_handler(MessageHandler(
        start, filters=command(BotCommands.StartCommand) & private))
    bot.add_handler(CallbackQueryHandler(
        token_callback, filters=regex(r'^pass')))
    bot.add_handler(MessageHandler(
        login, filters=command(BotCommands.LoginCommand) & private))
    bot.add_handler(MessageHandler(log, filters=command(
        BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(
        BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(
        BotCommands.PingCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
    bot.add_handler(MessageHandler(bot_help, filters=command(
        BotCommands.HelpCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
    bot.add_handler(MessageHandler(stats, filters=command(
        BotCommands.StatsCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
    LOGGER.info(f"WZML-X Bot [@{bot_name}] Started!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()
