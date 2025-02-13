import discord
from discord.ext import tasks
import os
from discord import player
import requests
import datetime
import time
import json
import re
import datetime
import dateutil
from dateutil.relativedelta import relativedelta
from requests.exceptions import URLRequired
from mergedeep import merge
import asyncio
from importlib import reload
import sys
import io
import traceback 
import socket
from concurrent.futures import ProcessPoolExecutor
from random import randrange
from word2number import w2n
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

last_activity = {}

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


allowed_categories = [
    '1305326699201691701', #EU1
    '1305326716281028650', #EU2
    '1305326700200202283', #US1
    '1305326717271019598', #US2
    '1305326706512625770', #Donations
    '1305326708148404315' #awaiting steam
]

used_channels = []
with open('channelids.txt') as f:
    used_channels = f.read().splitlines()
used_channels_ids = []
with open('channelids_steam.txt') as f:
    used_channels_ids = f.read().splitlines()
known_watchers = []
with open('watchlist.txt') as f:
    known_watchers = f.read().splitlines()
form_data = {}
ticket_close_timeout = {}
global admin_list
admin_list = {}
with open('admin_list.txt') as f:
    admin_list = json.load(f)
    f.close()

#admin_list = json.loads(requests.get("https://raw.githubusercontent.com/xdesignful/Admins/main/admins.json").content)

#admin_list = get_role_users()


api_relational = {
    "c5738674-bac8-4e04-94e7-bb121198fa2c": "-3z_eh1tNJ-ETNUQAR1XqygFlLa8ypqBsID0szosgeg=", #US1
    "unusedus2": "GR9xkEWQK9foq2tKBZL366fOvtEBAwXXQpJJcvLKhgk=", #US2
    "487c5364-157b-4824-ac55-21b025f7cec5": "Y8BxsROH58UILzJtBm-E7O3iP6XPEIWM4E3pLpjQqsY=", #EU1
    "unused": "5sjqjpo_qLMNGIhKm2Nqw6pLoFTBqcGn8hQyh94pAMo=" #EU2
}

server_ip = {
    "487c5364-157b-4824-ac55-21b025f7cec5": "64.40.9.198", #EU1
    "unused": "193.25.252.75", #EU2
    "c5738674-bac8-4e04-94e7-bb121198fa2c": "104.129.132.66", #US1
    "unusedus2": "195.60.167.138" #US2
}

webhook_msg = {
    "EU1" : "925722238844555294",
    "EU2" : "925722149602361394",
    "US1" : "925722238844555294",
    "US2" : "925722238844555294"
}
async def add_log(log_msg):
    channel = client.get_channel(1305326901388382242)
    await channel.send(log_msg)

# @tasks.loop(minutes=10)    
# async def webhook_async():
#     hook_status = {}
#     now = datetime.datetime.now().strftime("%H:%M | %d %B %Y")
#     for ip in server_ip.values():
#         hook_status[server_ip_to_name(ip)] = check_hooks(ip)
#         if hook_status[server_ip_to_name(ip)] == "up":
#             embed_color = 0x00ff00
#         else:
#             embed_color = 0xff0000
#         channel = client.get_channel(925709606137778206)
#         message = await channel.fetch_message(webhook_msg[server_ip_to_name(ip)])
#         embedVar = discord.Embed(title=server_ip_to_name(ip) + " Webhook is " + hook_status[server_ip_to_name(ip)], description=ip + ":9000", color=embed_color)
#         embedVar.set_footer(text="Last checked " + str(now) + " (EST)")
#         await message.edit(embed=embedVar)

def get_discord_id(message, discord_name):
    try:
        name, discriminator = discord_name.split('#')
        user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        return user
    except:
        return "0"

def check_vip_role(user):
    try:
        if user != "0":
            vip_role = discord.utils.get(user.guild.roles, id=1305326648421388338)
            if vip_role in user.roles:
                return "VIP role applied to <@" + str(user.id) + ">"
            else:
                return "VIP role failed to apply (User found but has no role)"
        else:
            return "VIP role failed to apply (user not found)"
    except:
        return "VIP role failed to apply (exception)"


async def apply_vip_role(user):
    try:
        guild = client.get_guild(1282699130363445380)
        member = guild.get_member(user.id)
        vip_role = discord.utils.get(user.guild.roles, id=1305326648421388338)
        await member.add_roles(vip_role)
    except:
        await add_log("Failed to apply priority")


async def check_vip_from_dm(steam64, server_ip, vip_steam_dc, message):
    try:
        cf_id = get_cf_from_steam64(steam64)
    except:
        cf_id = "failed"
    found = False
    all_dono = {}
    if cf_id != "failed":
        for server_id in server_ip.keys():
            server_name = server_ip_to_name(server_ip[server_id])
            all_dono[server_name] = check_prio(server_id)
        for server_donators in all_dono:
            for count, value in enumerate(all_dono[server_donators]['entries']):
                if not found:
                    if cf_id in value['user']['cftools_id']:
                        found = True
                        vip_steam_dc[steam64] = message.author.id
                        with open('vip_steam_dc.json', 'w') as filetowrite:
                            filetowrite.write(json.dumps(vip_steam_dc))
                        filetowrite.close()
                        embedVar = discord.Embed(title="VIP Status Found For " + steam64 + " in " + server_donators, description="VIP Role Applied", color=0x00ffe5)
                        embedVar.set_footer(text="")
                        await message.channel.send(embed=embedVar)
                        await message.delete()
                else:
                    break
    else:
        embedVar = discord.Embed(description="Invalid steam or steam already used")
        await message.channel.send(embed=embedVar)

def check_hooks(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((ip,9000))
    sock.close()
    if result == 0:
        return "up"
    else:
        return "down"

def get_role_users(message):
    r = discord.utils.get(message.guild.roles, id=1305326653873979484)
    admin_list = {}
    admin_list["213025853708304384"] = "ARTRIX"
    for member in r.members:
        admin_list[str(member.id)] = str(member.display_name)
    json_admin_list = json.dumps(admin_list)
    with open('admin_list.txt', 'w') as f:
        f.write(json_admin_list)
        f.close()
    return member, json_admin_list

def get_token():
    token_url = "https://data.cftools.cloud/v1/auth/register"
    token_data = {
        "application_id": "673e3a13cfad83829e42bd99",
        "secret": "ZDmfLp714/2nbPlJU8m/tirFz6z2Il6+Nqq1JECIfMU="
    }
    response = requests.post(token_url, data=token_data)
    token_response = json.loads(response.content)
    token = "Bearer " + token_response['token']
    return token

def get_cf_from_steam64(steam64):
    token = get_token()
    headers = {"Authorization": token}
    get_cf_url = "https://data.cftools.cloud/v1/users/lookup?identifier=" + steam64
    response = requests.get(get_cf_url, headers=headers)
    cftools_id_response = json.loads(response.content)
    cftools_id = cftools_id_response['cftools_id']
    return cftools_id
    

def ban_player(cftools_id, days, reason):
    a_date = datetime.datetime.now()
    a_month = dateutil.relativedelta.relativedelta(days=int(days))
    date_plus_month = a_date + a_month
    expiry = str(date_plus_month.isoformat())
    token = get_token()
    headers = {"Authorization": token}
    url = "https://data.cftools.cloud/v1/banlist/673e3a13cfad83829e42bd99/bans"
    if days == "0":
        data = {
            "format": "cftools_id",
            "identifier": cftools_id,
            "reason": reason,
            "expires_at": "3000-01-01T00:00:00+0000"
        }
    else:
        data = {
            "format": "cftools_id",
            "identifier": cftools_id,
            "reason": reason,
            "expires_at": expiry,
        }
    response = requests.post(url, data=data, headers=headers)
    return response


def vip_tag(steam64, server_id):
    try: 
        url = "http://" + server_ip[server_id] + ":9000/hooks/vip"
        data = {
            "one": "C:\\Josh\\vip.py",
            "-s":  "-s=" + str(steam64)
        }
        response = requests.get(url, data=data, timeout=1)
        return "VIP Tag Applied"
    except:
        #add_log("VIP Tag failed for " + str(steam64) + " with response: \'" + str(response.content) + "\' and payload: \'" + str(data) + "\' on server: " + str(url))
        return "VIP Tag NOT Applied due to error (Webhook unreachable)"

def server_ip_to_name(server_ip_address):
    server_name = "not found"
    if server_ip_address == "64.40.9.198": #eu1
        server_name = "EU1"
    if server_ip_address == "193.25.252.75": #eu2
        server_name = "EU2"
    if server_ip_address == "104.129.132.66": #us1
        server_name = "US1"
    if server_ip_address == "195.60.167.138": #us2
        server_name = "US2"
    return server_name

def check_vip(steam64):
    found_vip = {}
    for key, value in server_ip.items():
        try: 
            url = "http://" + value + ":9000/hooks/checkvip"
            data = {
                "one": "C:\\Josh\\checkvip.py",
                "-s":  "-s=" + str(steam64)
            }
            response = requests.get(url, data=data, timeout=1)
            found_vip[value] = re.sub(r'\W+', '', str(response.content))
        except:
            found_vip[value] = "Webhook Unavailable"
    return found_vip

def stash_log(server_id, days):
    try:
        url = "http://" + server_ip[server_id] + ":9000/hooks/stashlog"
        data = {
            "one": "C:\\Josh\\stash-dc.py",
            "-d": "-d=" + days
        }
        response = requests.get(url, data=data, timeout=1)
        return str(response.content)
    except:
        return "webhook unavailable"

def issue_prio(steam64, server_id, days, staff_member):
    a_date = datetime.datetime.now()
    a_month = dateutil.relativedelta.relativedelta(days=int(days))
    date_plus_month = a_date + a_month
    expiry = str(date_plus_month.isoformat())
    cftools_id = get_cf_from_steam64(steam64)
    token = get_token()
    headers = {"Authorization": token}
    url = "https://data.cftools.cloud/v1/server/" + server_id + "/queuepriority"
    response = requests.delete(url + "?cftools_id=" + cftools_id, headers=headers)
    data = {
        "api_key": api_relational[server_id],
        "cftools_id": cftools_id,
        "comment": "Approved by " + staff_member,
        "expires_at": expiry
    }
    response = requests.post(url, data=data, headers=headers)
    vip_msg = vip_tag(str(steam64), server_id)
    return vip_msg

def get_player_stats(cf_id):
    found = False
    for key in api_relational:
        token = get_token()
        url = "https://data.cftools.cloud/v2/server/" + key + "/player?cftools_id=" + cf_id
        headers = {"Authorization": token}
        response = requests.get(url, headers=headers)
        p_data = json.loads(response.content)
        if p_data["status"] == True:
            found = True
            found_p_data = p_data
    if found:
        return found_p_data
    else:
        return p_data
        

def update_prio():
    for key in api_relational:
        token = get_token()
        headers = {"Authorization": token}
        url = "https://data.cftools.cloud/v1/server/" + key + "/queuepriority"
        s = requests.Session()
        with s.get(url, headers=headers, stream=True) as resp:
            for line in resp.iter_lines():
                if line:
                    with open(key + '.json', 'wb') as the_file:
                        the_file.write(line)
        the_file.close()

def check_prio(server_id):
    update_prio()
    with open(server_id + '.json') as json_file:
        data = json.load(json_file)
    return data

def gt(dt_str):
    dt_str = dt_str.replace("Z", "")
    dt, _, us = dt_str.partition(".")
    dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
    return dt + datetime.timedelta()

def get_values(form_data):
    values_list = []
    now = datetime.datetime.now()
    day_name = now.strftime("%A")

    values = {
        # Admin
        "entry.839538034": form_data['admin'],
        # Steam64
        "entry.134731682": form_data['steam64'],
        # Discord name
        "entry.1128868252": form_data['discord_id'],
        # Ticket ID
        "entry.1832412248": form_data['ticket_id'],
        # Close msg
        "entry.1726715912": form_data['close_msg'],
    }

    values_list.append(values)

    return values_list

def send_gform(url, data, staff):
    for d in data:
        try:
            requests.post(url, data=d)
            asyncio.sleep(5)
            print("Form Submitted by " + str(staff))
        except:
            print("Error Occured! " + str(staff))

def get_values_dono(form_data):
    values_list = []
    now = datetime.datetime.now()
    day_name = now.strftime("%A")

    values = {
        # Admin
        "entry.172663717": form_data['admin'],
        # Steam64
        "entry.80174377": form_data['steam64'],
        # Discord name
        "entry.990330170": form_data['discord_id'],
        # Ticket ID
        "entry.80174377": form_data['ticket_id'],
    }

    values_list.append(values)

    return values_list

def send_gform_dono(url, data, staff):
    """It takes google form url which is to be submitted and also data which is a list of data to be submitted in the form iteratively."""

    for d in data:
        try:
            requests.post(url, data=d)
            print("Donation form Submitted by " + str(staff))
            asyncio.sleep(5)
        except:
            print("Error Occured! (Donation) " + str(staff))

def read_form_data():
    form_data_file = open("data.json", "r")
    form_data = form_data_file.read()
    return json.loads(form_data)

def read_dc_steam():
    dc_steam_file = open("steam-dc-data.json", "r")
    dc_steam = json.loads(dc_steam_file.read())
    return dc_steam

def read_ban_requests():
    ban_file = open("bans.json", "r")
    ban_data = ban_file.read()
    return json.loads(ban_data)

def update_dc_steam(dc_steam_new):
    dc_steam_file='steam-dc-data.json' 
    with open(dc_steam_file, 'w') as filetowrite:
        filetowrite.write(json.dumps(dc_steam_new))
        
    
def check_high_prio(item_list):
    high_prio_items = [
        "B_Improvised_C4",
        "B_C4",
        "RA_Gunpowder",
        "JD_RPG",
        "Ammo_JD_RPG_Rocket",
        "Explode_Pack",
        "Keycard_Green",
        "Keycard_Blue",
        "Keycard_Red",
        "Keycard_Yellow",
        "Keycard_Purple",
        "Keycard_Black",
        "Toxicm18SmokeGrenade_Red",
        "Toxicm18SmokeGrenade_Green",
        "Toxicm18SmokeGrenade_Purple",
        "Toxicm18SmokeGrenade_Yellow",
        "Toxicm18SmokeGrenade_White",
        "grenade_chemgas",
        "ammo_40mm_explosive"
    ]
    escalate = False
    for item in item_list:
        if item in high_prio_items:
            escalate = True
            break
        else:
            pass
    return escalate

def comp_items(item_list, steam64, server):
    token = get_token()
    session_id = get_session_id(steam64, server, token)
    print(session_id)
    if not session_id == "None":
        headers = {"Authorization": token}
        comp_url = "https://data.cftools.cloud/v1/server/" + server + "/GameLabs/action"
        for item in item_list:
            post_data = {
                "actionCode": "CFCloud_SpawnPlayerItem",
                "actionContext": "player",
                "referenceKey": steam64,
                "parameters": {
                    "item": {
                        "dataType": "string",
                        "valueString": item
                    },
                    "quantity": {
                        "dataType": "int",
                        "valueInt": "1"
                    }
                }
            }
            response = requests.post(comp_url, json=post_data, headers=headers)
            print(response.status_code)
            print(response.text)

""" def comp_items(item_list, steam64, server):
    token = get_token()
    session_id = get_session_id(steam64, server, token)
    print(session_id)
    if not session_id == "None":
        headers = {"Authorization": token}
        comp_url = "https://data.cftools.cloud/v1/server/" + server + "/GameLabs/action"
        for item in item_list:
            post_data = {
                "actionCode": "CFCloud_SpawnPlayerItem",
                "actionContext": "player",
                "referenceKey": session_id,
                "item": item,
                "quantity": "1"
            }
            response = requests.post(comp_url, data=post_data, headers=headers) """
            
""" def comp_items(item_list, steam64, server):
    token = get_token()
    session_id = get_session_id(steam64, server, token)
    print(session_id)
    if not session_id == "None":
        headers = {"Authorization": token}
        comp_url = "https://data.cftools.cloud/v0/server/" + server + "/gameLabs/spawn"
        for item in item_list:
            post_data = {
                "gamesession_id": session_id,
                "object": item,
                "quantity": "1"
            }
            response = requests.post(comp_url, data=post_data, headers=headers) """

def get_session_id(steam64, server, token,):
    headers = {"Authorization": token}
    response = requests.get("https://data.cftools.cloud/v1/server/" + server + "/GSM/list", headers=headers)
    raw_data = json.loads(response.content)
    live_pos = {}
    i = 0
    session_id = "None"
    for sessions in raw_data['sessions']:
        if steam64 in sessions['gamedata']['steam64']:
            session_id = sessions['id']
    return session_id

"""def generate_math_problem(solution):
    import random
    x = random.randint(1, 99)
    y = random.randint(1, 99)
    z = random.randint(1, 99)
    c = random.randint(1, 4)
    list_random_ints = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 25, 30, 35, 36, 37, 38]
    if c == 1:
        nonzero = x * y + z
        takeaway = nonzero - solution
        math_string = str(x) + " x " + str(y) + " + " + str(z) + " - " + str(takeaway)
    if c == 2:
        found = False
        divisors = []
        while found == False:
            for x_int in list_random_ints:
                if x % x_int == 0:
                    divisors.append(x_int)
            if divisors:
                found = True
            else:
                x = random.randint(1, 99)
        w = random.choice(divisors)
        nonzero = x / w + y
        takeaway = nonzero - solution
        math_string = str(x) + " / " + str(w) + " + " + str(y) + " - " + str(takeaway)
    if c == 3:
        nonzero = x + y + z
        takeaway = nonzero - solution
        math_string = str(x) + " + " + str(y) + " + " + str(z) + " - " + str(takeaway)
    if c == 4:
        nonzero = x + y + z
        takeaway = nonzero - solution
        math_string = str(x) + " + " + str(y) + " + " + str(z) + " - " + str(takeaway)

    return math_string"""
        
        

bot_msg_d = {}
old_form_data = read_form_data()
comp_request = {}

intents = discord.Intents.default()  # Allow the use of custom intents
intents.members = True

client = discord.Client(intents=intents)

#client = discord.Client()
discord_id = {}

dc_steam = read_dc_steam()
old_ban_data = read_ban_requests()


async def update_ticket_perms(message):
    server_roles = {
        "eu1": 1305326662933807134,
        "eu2": 1305326663961411716,
        "us1": 1305326665181827082,
        "us2": 1305326666087923712,
        "donations": 1305326679949971487,
        "nps": 1305326666989441064
    }
    
    #await message.channel.send("<@" + str(server_roles["eu1"]) + ">")
    if "eu1" in message.channel.name.lower():
        server = "eu1"
        for server_id in server_roles:
            if not server_id == server:
                staff_role = discord.utils.get(message.guild.roles, id=server_roles[server_id])
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = True
                overwrite.read_messages = True
                await message.channel.set_permissions(staff_role, overwrite=overwrite)
            category_obj = discord.utils.get(message.guild.channels, id=1305326699201691701)
            await message.channel.edit(category=category_obj)

    elif "eu2" in message.channel.name.lower():
        server = "eu2"
        for server_id in server_roles:
            if not server_id == server:
                staff_role = discord.utils.get(message.guild.roles, id=server_roles[server_id])
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = True
                overwrite.read_messages = True
                await message.channel.set_permissions(staff_role, overwrite=overwrite)
            category_obj = discord.utils.get(message.guild.channels, id=1305326716281028650)
            await message.channel.edit(category=category_obj)

    elif "us1" in message.channel.name.lower():
        server = "us1"
        for server_id in server_roles:
            if not server_id == server:
                staff_role = discord.utils.get(message.guild.roles, id=server_roles[server_id])
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = True
                overwrite.read_messages = True
                await message.channel.set_permissions(staff_role, overwrite=overwrite)
            category_obj = discord.utils.get(message.guild.channels, id=1305326700200202283)
            await message.channel.edit(category=category_obj)

    elif "us2" in message.channel.name.lower():
        server = "us2"
        for server_id in server_roles:
            if not server_id == server:
                staff_role = discord.utils.get(message.guild.roles, id=server_roles[server_id])
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = True
                overwrite.read_messages = True
                await message.channel.set_permissions(staff_role, overwrite=overwrite)
            category_obj = discord.utils.get(message.guild.channels, id=1305326717271019598)
            await message.channel.edit(category=category_obj)

    elif "donations" in message.channel.name.lower():
        server = "donations"
        for server_id in server_roles:
            if not server_id == server:
                staff_role = discord.utils.get(message.guild.roles, id=server_roles[server_id])
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = True
                overwrite.read_messages = True
                await message.channel.set_permissions(staff_role, overwrite=overwrite)
            category_obj = discord.utils.get(message.guild.channels, id=1305326706512625770)
            await message.channel.edit(category=category_obj)

    else:
        server = "failed"

@tasks.loop(minutes=1)
async def check_inactivity():
    current_time = datetime.datetime.now()
    to_remove = []
    
    for channel_id, last_time in last_activity.items():
        if (current_time - last_time).total_seconds() >= 1800:  # 30 minutes
            to_remove.append(channel_id)
    
    for channel_id in to_remove:
        channel = client.get_channel(channel_id)
        if channel:
            try:
                # Preserve original unclaim logic
                current_name = channel.name
                new_name = current_name
                for i in admin_list.values():
                    admin_name = re.sub(r'\W+', '', str(i)).lower()
                    if admin_name in current_name.lower():
                        new_name = current_name.replace(admin_name + "-", "")
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                
                await channel.edit(name=new_name)
                embedVar = discord.Embed(description='🎟️ Ticket automatically unclaimed due to 30 minutes of inactivity')
                await channel.send(embed=embedVar)
                await add_log(f"Ticket {channel.id} unclaimed due to inactivity")
            except Exception as e:
                print(f"Error unclaiming ticket: {e}")
            finally:
                del last_activity[channel_id]

@client.event
async def on_ready():
    await add_log('BOT REBOOTED')
    check_inactivity.start()
    #webhook_async.start()
    read_form_data()

@client.event
async def on_raw_reaction_add(payload):
    global admin_list
    channel = client.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    mod_role = discord.utils.get(message.guild.roles, id=1305326561347764254)
    emoji_list = ['📌', '🟢', '🔴', '🟠', '🟡', '⚫','🕙', '🆔']
    if str(channel.id) == "862617931766300673":
        msg_id = message.embeds[0].description
        if str(payload.emoji) == "✅" :
            if not mod_role in payload.member.roles and not payload.user_id == 1300850899580747957:
                await message.channel.send('Ban request approved by: ' + payload.member.display_name)
                full_bans = read_ban_requests()
                cftools_id = full_bans[msg_id]["cf_id"]
                days = full_bans[msg_id]["days"]
                reason = full_bans[msg_id]["reason"]
                ban_player(cftools_id, days, reason)
                await message.remove_reaction("✅", payload.member)
                channel = client.get_channel(840225718696673330) # ban-list
                await channel.send(cftools_id + " got banned via API: " + reason)
                await add_log("Ban issued for " + cftools_id)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("✅", payload.member)


        if str(payload.emoji) == "❌" :
            if not mod_role in payload.member.roles and not payload.user_id == 1300850899580747957:
                await message.channel.send('Ban request denied by: ' + payload.member.display_name)
                await message.remove_reaction("❌", payload.member)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("❌", payload.member)

            
    if str(channel.category.id) in allowed_categories:

        if str(payload.emoji) == "📌":
            if str(payload.user_id) in admin_list:
                ticket_owner = re.sub(r'\W+', '', str(payload.member.display_name)).lower()
                if "ARTRIX" in ticket_owner:
                    ticket_owner = "🍆-" + ticket_owner
                new_name = str(channel.name)
                
                # Existing name cleanup logic
                for i in admin_list.values():
                    admin_name = re.sub(r'\W+', '', str(i)).lower()
                    if admin_name in str(channel.name):
                        new_name = new_name.replace(admin_name + "-", "")
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")

                if ticket_owner in str(channel.name):
                    # Manual unclaim
                    new_name = new_name.replace(ticket_owner + "-", "")
                    embedVar = discord.Embed(description=f'Ticket has been unclaimed by {payload.member.display_name}')
                    # Remove from activity tracking
                    if channel.id in last_activity:
                        del last_activity[channel.id]
                else:
                    # Manual claim
                    new_name = f"{ticket_owner}-{new_name}"
                    embedVar = discord.Embed(description=f'Ticket has been claimed by {payload.member.display_name}')
                    # Start tracking activity
                    last_activity[channel.id] = datetime.datetime.now()

                await channel.edit(name=new_name)
                await message.remove_reaction("📌", payload.member)
                await message.channel.send(embed=embedVar)
                log_channel = client.get_channel(1305326901388382242)
                await log_channel.send(f"📌 used by {payload.member.display_name} in {new_name}")

        elif str(payload.emoji) == "🟢" :
            if str(payload.user_id) in admin_list:
                new_name = str(channel.name).lower()
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                staff_name = re.sub(r'\W+', '', str(payload.member.display_name)).lower()
                new_name = "🟢-" + new_name.replace(str(staff_name.replace(' ', '-')), "")
                await channel.edit(name = new_name) 
                await message.remove_reaction("🟢", payload.member)
                await message.channel.send("<@&1305326561347764254>") #Mod
                embedVar = discord.Embed(description="Ticket has been relegated by: " + str(payload.member.display_name), color=0x2eac1a)
                await message.channel.send(embed=embedVar)
                channel = client.get_channel(1305326901388382242)
                await channel.send("🟢 used by " + payload.member.display_name + " in " + new_name)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("🟢", payload.member)

        elif str(payload.emoji) == "🔴" :
            if str(payload.user_id) in admin_list:
                new_name = str(channel.name).lower()
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                staff_name = re.sub(r'\W+', '', str(payload.member.display_name)).lower()
                new_name = "🔴-" + new_name.replace(str(staff_name.replace(' ', '-')), "")
                await channel.edit(name = new_name) 
                await message.remove_reaction("🔴", payload.member)
                await message.channel.send("<@&1305326559355207690> <@&1305326559976226929>") #Admin & Trial Admin
                embedVar = discord.Embed(description="Ticket has been escalated by: " + str(payload.member.display_name), color=0xff0000)
                await message.channel.send(embed=embedVar)
                channel = client.get_channel(1305326901388382242)
                await channel.send("🔴 used by " + payload.member.display_name + " in " + new_name)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("🔴", payload.member)



        elif str(payload.emoji) == "🟡" :
            if str(payload.user_id) in admin_list:
                new_name = str(channel.name).lower()
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                staff_name = re.sub(r'\W+', '', str(payload.member.display_name)).lower()
                new_name = "🟡-" + new_name.replace(str(staff_name.replace(' ', '-')), "")
                await channel.edit(name = new_name) 
                await message.remove_reaction("🟡", payload.member)
                await message.channel.send("<@&1305326556368867389>") #Exec
                embedVar = discord.Embed(description="Ticket has been escalated by: " + str(payload.member.display_name), color=0xe40ed7)
                await message.channel.send(embed=embedVar)
                channel = client.get_channel(1305326901388382242)
                await channel.send("🟡 used by " + payload.member.display_name + " in " + new_name)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("🟡", payload.member)



        elif str(payload.emoji) == "🟠" :
            if str(payload.user_id) in admin_list:
                new_name = str(channel.name).lower()
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                staff_name = re.sub(r'\W+', '', str(payload.member.display_name)).lower()
                new_name = "🟠-" + new_name.replace(str(staff_name.replace(' ', '-')), "")
                await channel.edit(name = new_name) 
                await message.remove_reaction("🟠", payload.member)
                await message.channel.send("<@&1305326557404856371><@&1305326558373871737>") #Head admin & Sr Admin
                embedVar = discord.Embed(description="Ticket has been escalated by: " + str(payload.member.display_name), color=0xff4900)
                await message.channel.send(embed=embedVar)
                channel = client.get_channel(1305326901388382242)
                await channel.send("🟠 used by " + payload.member.display_name + " in " + new_name)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("🟠", payload.member)

        elif str(payload.emoji) == "⚫" :
            if str(payload.user_id) in admin_list:
                new_name = str(channel.name).lower()
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                staff_name = re.sub(r'\W+', '', str(payload.member.display_name)).lower()
                new_name = "⚫-" + new_name.replace(str(staff_name.replace(' ', '-')), "")
                await channel.edit(name = new_name) 
                await message.remove_reaction("⚫", payload.member)
                await message.channel.send("<@&1305326555240599602>") #Owner
                embedVar = discord.Embed(description="Ticket has been escalated by: " + str(payload.member.display_name), color=0x000000)
                await message.channel.send(embed=embedVar)
                channel = client.get_channel(1305326901388382242)
                await channel.send("⚫ used by " + payload.member.display_name + " in " + new_name)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("⚫", payload.member)

        elif str(payload.emoji) == "🕙" :
            if str(payload.user_id) in admin_list:
                new_name = str(channel.name).lower()
                if "🕙" in new_name:
                    new_name = new_name.replace("🕙", "")
                else:
                    for i in emoji_list:
                        new_name = new_name.replace(i + "-", "")
                    staff_name = re.sub(r'\W+', '', str(payload.member.display_name)).lower()
                    new_name = "🕙-" + new_name.replace(str(staff_name.replace(' ', '-')), "")
                    await message.channel.send('>>> Waiting on response from ticket creator.') #Wait
                    await message.channel.send('>>> You can type `$remind <time in minutes> <reason>` to set a reminder for yourself')
                await channel.edit(name = new_name) 
                await message.remove_reaction("🕙", payload.member)
                channel = client.get_channel(1305326901388382242)
                await channel.send("🕙 used by " + payload.member.display_name + " in " + new_name)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("🕙", payload.member)

        elif str(payload.emoji) == "🆔" :
            if str(payload.user_id) in admin_list:
                new_name = str(channel.name)
                await message.remove_reaction("🆔", payload.member)
                cf_id = get_cf_from_steam64(form_data[str(channel.id)]['steam64'])
                embed=discord.Embed(color=0x00ffe5)
                embed.add_field(name="CFTools URL", value="https://app.cftools.cloud/profile/" + cf_id, inline=False)
                await message.channel.send(embed=embed)
                channel = client.get_channel(1305326901388382242)
                await channel.send("🆔 used by " + payload.member.display_name + " in " + new_name)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("🆔", payload.member)

        if str(payload.emoji) == "✅" and str(payload.user_id) in admin_list and "comp" in str(message.channel.name).lower():
            if not mod_role in payload.member.roles and not payload.user_id == 1300850899580747957:
                if comp_request[payload.channel_id]["approved"] == False:
                    await message.channel.send('Comp request approved by: ' + payload.member.display_name)
                    item_list = comp_request[payload.channel_id]["item_list"]
                    steam64 = comp_request[payload.channel_id]["steam64"]
                    server = comp_request[payload.channel_id]["server"]
                    #comp_items(item_list, steam64, server)
                    await message.remove_reaction("✅", payload.member)
                    await add_log("Comp approved by " + str(payload.member.display_name))
                    comp_request[message.channel.id]["approved"] = True
                    embed_title = "Your comp has been approved."
                    embed_desc = "Follow the below instructions to receive your gear"
                    embedVar = discord.Embed(title=embed_title, description=embed_desc, color=discord.Color.blue())
                    embedVar.add_field(name="Be Online and Be Safe", value="Before completing this action make sure you are ONLINE and in a SAFE PLACE", inline=False)
                    embedVar.add_field(name="Once you are ready", value="Type in this channel with \"I AM IN-GAME AND SAFE\" (case sensitive no quotes)", inline=False)
                    embedVar.add_field(name="What will happen?", value="The gear you have been comp'd will spawn at your feet.", inline=False)
                    embedVar.add_field(name="Disclaimer", value="If you accept the comp by typing \"I AM IN-GAME AND SAFE\" and you are offline, unsafe etc - staff are not responsible and will not comp you again", inline=False)
                    await message.channel.send(embed=embedVar)
                else:
                    await add_log("Someone tried to approve an already approved thing")


                new_name = str(message.channel.name).lower()
                new_name = new_name.replace("comp-", "")
                emoji_list = ['📌', '🟢', '🔴', '🟠', '🟡', '⚫','🕙', '🆔']
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                new_name = "🕧-comp-" + new_name
                await message.channel.edit(name = new_name)

            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("✅", payload.member)


        if str(payload.emoji) == "❌" :
            if not mod_role in payload.member.roles and not payload.user_id == 1300850899580747957:
                await message.channel.send('Comp request denied by: ' + payload.member.display_name)
                await message.remove_reaction("❌", payload.member)
            else:
                if not payload.user_id == 1300850899580747957:
                    await message.remove_reaction("❌", payload.member)

        

@client.event
async def on_message(message):
    with open('lastmessage.log', 'w') as filetowrite:
        filetowrite.write(message.content + ("\n"))
    filetowrite.close()
    global admin_list
    admin_headers = {
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    # emoji_list = ['🎄']
    # if not message.author.id == 1300850899580747957: 
    #     for i in emoji_list:
    #         await message.add_reaction(i)
    #admin_list = json.loads(requests.get("https://raw.githubusercontent.com/xdesignful/Admins/main/admins.json", headers=admin_headers).content)
    if message.guild and str(message.channel.category.id) in allowed_categories:
        if not message.author.bot and message.channel.id in last_activity:
            # Reset activity timer on any user message
            last_activity[message.channel.id] = datetime.datetime.now()
    if not message.guild:
        #if "sawubona" in str(message.content).lower(): 
        #    await message.channel.send("The door code is 81273 - the location is the key for the code you already solved, in a place you may have already been if you competed in a previous event.")
        #    with open('solvers.txt', 'a') as the_file:
        #            the_file.write(str(message.author) + '\n')
        if "$vip" in str(message.content).lower():
            embedVar = discord.Embed(description='Searching for VIP membership... this takes some time! Please be patient.')
            await message.channel.send(embed=embedVar)
            guild = client.get_guild(1282699130363445380)
            vip_str = str(message.content).split()
            steam64 = vip_str[1]
            
            with open('vip_steam_dc.json') as f:
                vip_steam_dc = json.load(f)
                f.close()
            vip_msg = check_vip_role(message.author)
            if "role applied to" in vip_msg or str(message.author.id) in admin_list:
                embedVar = discord.Embed(description='You already have the VIP role (or better!)')
                await message.channel.send(embed=embedVar)
            elif steam64 in vip_steam_dc.keys():
                embedVar = discord.Embed(description="This steam has already been claimed by: <@" + str(vip_steam_dc[steam64]) + ">")
                await message.channel.send(embed=embedVar)
            else:
                await check_vip_from_dm(steam64, server_ip, vip_steam_dc, message)
                

    else:
        mod_role = discord.utils.get(message.guild.roles, id=1305326561347764254)
        asshole = discord.utils.get(message.guild.roles, id=1305326678750400552)
        staff_role = discord.utils.get(message.guild.roles, id=1305326653873979484)
        if str(message.channel.id) == "1305326810124390481" or str(message.channel.id) == "1305326811286077440":
            if "$suggest" in str(message.content).lower():
                suggest_str = str(message.content).split()
                if len(suggest_str) == 0:
                    await message.delete()
                else:
                    suggest_str.pop(0)
                    suggest_str = ' '.join(suggest_str)
                    if str(message.channel.id) == "1305326810124390481": 
                        embed=discord.Embed(title=str(message.author), color=0x00ffe5)
                        embed.set_thumbnail(url=message.author.avatar_url)
                        embed.add_field(name="Suggestion: ", value=suggest_str, inline=False)
                        embed.set_footer(text="Command: $suggest <suggestion>")
                        await message.channel.send(embed=embed)
                        await message.delete()
                        await add_log("New suggestion by " + str(message.author))
                    if str(message.channel.id) == "1305326811286077440": #Events
                        embed=discord.Embed(title=str(message.author), color=0x00ffe5)
                        embed.set_thumbnail(url=message.author.avatar_url)
                        embed.add_field(name="Event Suggestion: ", value=suggest_str, inline=False)
                        embed.set_footer(text="Command: $suggest <suggestion>")
                        await message.channel.send(embed=embed)
                        await message.delete()
                        await add_log("New event suggestion by " + str(message.author))
            if str(message.author.id) == "235148962103951360" or str(message.author.id) in admin_list or str(message.author.id) == "1300850899580747957":
                if str(message.author.id) == "235148962103951360":
                    if "weed" in str(message.embeds[0].description).lower() and "mod" in str(message.embeds[0].description).lower():
                        await message.reply("No.")
            elif str(message.author.id) == "1300850899580747957":
                pass
            else:
                await message.delete()

        elif str(message.channel.category.id) in allowed_categories:
            #This is the ticket categories               
            channel_id = str(message.channel.id)
            seen = used_channels
            seen_id = used_channels_ids
            if "$fixticket" in str(message.content) and str(message.author.id) in admin_list:
                await update_ticket_perms(message)
                await asyncio.sleep(0.5)
                await message.channel.send("<@&1305326561347764254>")
                await asyncio.sleep(0.5)
                embedVar = discord.Embed(title="Ticket Control Panel", description="You are seeing this as ticket was fixed", color=0x00ffe5)
                embedVar.add_field(name="Manual ticket fix applied", value="Some commands may fail (verify, check etc)", inline=False)
                embedVar.set_footer(text="")
                await message.channel.send(embed=embedVar)
                
            if str(channel_id) not in seen or not channel_id in form_data:
                bot_msg_d[channel_id] = {}
                form_data[channel_id] = {}
                if channel_id in old_form_data:
                    form_data[channel_id] = old_form_data[channel_id]
                else:
                    form_data[channel_id] = {}
                    form_data[channel_id]['steam64'] = ""
                seen.append(channel_id)
                used_channels.append(channel_id)
                if str(message.author) in ["Ticket Tool#6207"]:
                    split_msg = str(message.content).split()
                    discord_id[channel_id] = re.sub("[^0-9]", "", split_msg[1])
                    await message.delete()
                    await message.channel.send(str(message.content))
                    if discord_id[channel_id] in dc_steam.keys():
                        #embedVar = discord.Embed(title="Welcome back, we remembered you! Don't enter your steam.", description="Please enter your issue below, with as much evidence and detail as possible!", color=0x00ffe5)
                        #await message.channel.send(embed=embedVar)
                        used_channels_ids.append(channel_id)
                        form_data[channel_id] = {}
                        form_data[channel_id]['ticket_id'] = re.sub(r'\W+', '', str(message.channel.name)).lower()
                        form_data[channel_id]['discord_id'] = discord_id[channel_id] #Convert this to author not ID
                        form_data[channel_id]['steam64'] = dc_steam[discord_id[channel_id]]
                        form_data[channel_id]['submitted'] = False
                        cf_id = get_cf_from_steam64(form_data[channel_id]['steam64'])
                        player = get_player_stats(cf_id)
                        if player["status"] == False:
                            p_name = "Player has not played on this server."
                        else:
                            p_name = player[cf_id]["omega"]["name_history"]
                            p_name = ', '.join(p_name)
                        await asyncio.sleep(0.5)
                        await update_ticket_perms(message)
                        await asyncio.sleep(0.5)
                        await message.channel.send("<@&1305326561347764254>")
                        embedVar = discord.Embed(title="If this is not your Steam64 ID please let a member of staff know", description=dc_steam[discord_id[channel_id]], color=0x00ffe5)
                        embedVar.add_field(name="Known in-game names:", value=p_name, inline=False)
                        embedVar.set_footer(text="")
                        await message.channel.send(embed=embedVar)
                        ticket_close_timeout[str(message.channel.id)] = False
                        with open('channelids_steam.txt', 'a') as the_file:
                            the_file.write(str(channel_id) + '\n')
                        combi_form_data = merge(form_data, old_form_data)
                        a_file = open("data.json", "w")
                        json.dump(combi_form_data, a_file)
                        a_file.close()
                    else:
                        if "$steam64" not in str(message.content) or str(message.author.id) not in admin_list:
                            embedVar = discord.Embed(title='Staff cannot see this ticket right now', \
                            description='You need to enter your steam64 ID or steam community URL in the chat below to continue.', color=0x00ffe5)
                            embedVar.add_field(name="Not sure how?", value="type $steam64 in this chat", inline=False)
                            embedVar.set_footer(text="This ticket will auto-close in 30 minutes if no response is received.")
                            await message.channel.send(embed=embedVar)
                            ticket_close_timeout[str(message.channel.id)] = True
                            await asyncio.sleep(1800)
                            if ticket_close_timeout[str(message.channel.id)]:
                                await message.channel.delete(reason="No response")
                        else:
                            pass
                    with open('channelids.txt', 'a') as the_file:
                        the_file.write(str(channel_id) + '\n')
                    combi_form_data = merge(form_data, old_form_data)
                    a_file = open("data.json", "w")
                    json.dump(combi_form_data, a_file)
                    a_file.close()
                
            try:
                if not 'bot_msg' in bot_msg_d[channel_id].keys():
                    bot_msg_d[channel_id]['bot_msg'] = []
            except:
                pass
            if str(message.author) in ["Bastion#7773"]:
                bot_msg_d[channel_id]['bot_msg'].append(message)
            if str(channel_id) not in seen_id and not "Bastion" in str(message.author) and not \
                "Ticket" in str(message.author) and not \
                    str(message.author.id) in dc_steam.keys():
                check_steam_id_msg = re.findall('[0-9]+', str(message.content))
                for c in check_steam_id_msg:
                    if len(c) > 15 and len(c) < 19:
                        form_data[channel_id]['steam64'] = c
                        steam_response_raw = requests.get("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0001/?key=E5D346B22C99757B8BF8681253CDDFB4&steamids=" + str(message.content))
                        steam_response = json.loads(steam_response_raw.content)
                        if "[null" in str(steam_response_raw.content):
                            #await message.channel.send(">>> Please enter a valid Steam64 ID or Steam Community URL to receive admin assistance. Type `$steam64` to learn how.")
                            embedVar = discord.Embed(title='Staff cannot see this ticket, no help will be provided.', \
                            description='The steam ID you provided was invalid. Please try again.', color=0x00ffe5)
                            embedVar.add_field(name="Not sure how?", value="type $steam64 in this chat", inline=False)
                            await message.channel.send(embed=embedVar)
                            form_data[channel_id]['steam64'] = ''
                        else:
                            used_channels_ids.append(channel_id)
                            for x in bot_msg_d[channel_id]['bot_msg']:
                                await x.delete()
                            form_data[channel_id]['ticket_id'] = re.sub(r'\W+', '', str(message.channel.name)).lower()
                            form_data[channel_id]['discord_id'] = str(message.author)
                            form_data[channel_id]['steam64'] = c
                            form_data[channel_id]['submitted'] = False
                            cf_id = get_cf_from_steam64(form_data[channel_id]['steam64'])
                            player = get_player_stats(cf_id)
                            if player["status"] == False:
                                p_name = "Player has not played on this server."
                            else:
                                p_name = player[cf_id]["omega"]["name_history"]
                                p_name = ', '.join(p_name)
                            await update_ticket_perms(message)
                            await asyncio.sleep(0.5)
                            await message.channel.send("<@&1305326561347764254>")
                            await asyncio.sleep(0.5)
                            if "steamcommunity" in str(message.content):
                                steam64 =  c
                                embed_title = "If this is not your Steam64 ID please let a member of staff know"
                            else:
                                steam64 = steam_response['response']['players']['player'][0]['profileurl']
                                embed_title = "If this is not your Steam URL please let a member of staff know"
                            embedVar = discord.Embed(title=embed_title, description=steam64, color=0x00ffe5)
                            embedVar.add_field(name="Known in-game names:", value=p_name, inline=False)
                            embedVar.set_footer(text="")
                            await message.channel.send(embed=embedVar)
                            ticket_close_timeout[str(message.channel.id)] = False
                            with open('channelids_steam.txt', 'a') as the_file:
                                the_file.write(str(channel_id) + '\n')
                            combi_form_data = merge(form_data, old_form_data)
                            a_file = open("data.json", "w")
                            json.dump(combi_form_data, a_file)
                            a_file.close()
                            dc_steam[str(message.author.id)] = str(form_data[channel_id]['steam64'])
                            update_dc_steam(dc_steam)
                            break
                if "steamcommunity.com" in str(message.content) and not \
                    "Bastion" in str(message.author) and not \
                        "Ticket" in str(message.author) and \
                            form_data[channel_id]['steam64'] == "":
                        used_channels_ids.append(channel_id)
                        vanity = re.search("(?P<url>https?://[^\s]+)", str(message.content)).group("url")
                        #vanity = vanity.split()
                        vanity = vanity.replace("https://steamcommunity.com/", "")
                        vanity = vanity.replace("/","")
                        vanity = vanity.replace("profiles","")
                        vanity = vanity.replace("profile","")
                        vanity = vanity.replace("id","")
                        steam_response_raw = requests.get("http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=E5D346B22C99757B8BF8681253CDDFB4&vanityurl=" + vanity)
                        steam_response = json.loads(steam_response_raw.content)
                        if "No match" in str(steam_response):
                            #await message.channel.send(">>> Please enter a valid Steam64 ID or Steam Community URL to receive admin assistance. Type `$steam64` to learn how.")
                            embedVar = discord.Embed(title='Staff cannot see your ticket until you enter your STEAM64 ID or STEAM COMMUNITY URL', \
                            description='type the command $steam64 in this ticket if you are not sure how to find your steam 64 ID', color=0x00ffe5)
                            await message.channel.send(embed=embedVar)
                        else:
                            for x in bot_msg_d[channel_id]['bot_msg']:
                                    await x.delete()
                            form_data[channel_id] = {}
                            form_data[channel_id]['ticket_id'] = re.sub(r'\W+', '', str(message.channel.name)).lower()
                            form_data[channel_id]['discord_id'] = str(message.author)
                            form_data[channel_id]['steam64'] = steam_response['response']['steamid']
                            form_data[channel_id]['submitted'] = False
                            cf_id = get_cf_from_steam64(form_data[channel_id]['steam64'])
                            player = get_player_stats(cf_id)
                            if player["status"] == False:
                                p_name = "Player has not played on this server."
                            else:
                                p_name = player[cf_id]["omega"]["name_history"]
                                p_name = ', '.join(p_name)
                            await update_ticket_perms(message)
                            await asyncio.sleep(0.5)
                            await message.channel.send("<@&1305326561347764254>")
                            await asyncio.sleep(0.5)
                            embedVar = discord.Embed(title="If this is not your Steam64 ID please let a member of staff know", description=steam_response['response']['steamid'], color=0x00ffe5)
                            embedVar.add_field(name="Known in-game names:", value=p_name, inline=False)
                            embedVar.set_footer(text="")
                            await message.channel.send(embed=embedVar)
                            ticket_close_timeout[str(message.channel.id)] = False
                            with open('channelids_steam.txt', 'a') as the_file:
                                the_file.write(str(channel_id) + '\n')
                            combi_form_data = merge(form_data, old_form_data)
                            a_file = open("data.json", "w")
                            json.dump(combi_form_data, a_file)
                            a_file.close()
                            dc_steam[str(message.author.id)] = str(form_data[channel_id]['steam64'])
                            update_dc_steam(dc_steam)
                else:
                    if form_data[channel_id]['steam64'] == "" and str(message.author) not in ["Ticket Tool#6207"] and str(message.author) not in ["Bastion#7773"]:
                        if str(message.author.id) not in admin_list:
                            #await message.channel.send(">>> Please enter your Steam64 ID or Steam Community URL to receive admin assistance")
                            if "$steam64" not in str(message.content) or str(message.author.id) not in admin_list:
                                embedVar = discord.Embed(title='Staff cannot see this ticket right now', \
                                description='You need to enter your steam64 ID or steam community URL in the chat below to continue.', color=0x00ffe5)
                                embedVar.add_field(name="Not sure how?", value="type $steam64 in this chat", inline=False)
                                embedVar.set_footer(text="This ticket will auto-close in 30 minutes if no response is received.")
                            await message.channel.send(embed=embedVar)
                        if "$" in str(message.content):
                            await message.delete()

            elif str(channel_id) not in seen_id and not "Bastion" in str(message.author) and not \
                "Ticket" in str(message.author) and \
                    str(message.author.id) in dc_steam.keys():
                if str(message.author.id) in admin_list and str(message.author.id) != "213025853708304384":
                    if "$" or "@" in str(message.content):
                        pass
                    else:
                        await message.delete()
                        await message.author.send("Do not help people until they have provided a steam ID. Your original message is below: ")
                        await message.author.send(str(message.content))
                        await add_log(str(message.author) + " tried to help without a Steam64 ID in " + str(message.channel))   

                else:
                    used_channels_ids.append(channel_id)
                    form_data[channel_id] = {}
                    form_data[channel_id]['ticket_id'] = re.sub(r'\W+', '', str(message.channel.name)).lower()
                    form_data[channel_id]['discord_id'] = str(message.author)
                    form_data[channel_id]['steam64'] = dc_steam[str(message.author.id)]
                    form_data[channel_id]['submitted'] = False
                    cf_id = get_cf_from_steam64(form_data[channel_id]['steam64'])
                    player = get_player_stats(cf_id)
                    if player["status"] == False:
                        p_name = "Player has not played on this server."
                    else:
                        p_name = player[cf_id]["omega"]["name_history"]
                        p_name = ', '.join(p_name)
                    await asyncio.sleep(0.5)
                    await update_ticket_perms(message)
                    await asyncio.sleep(0.5)
                    await message.channel.send("<@&1305326561347764254>")
                    embedVar = discord.Embed(title="If this is not your Steam64 ID please let a member of staff know", description=dc_steam[str(message.author.id)], color=0x00ffe5)
                    embedVar.add_field(name="Known in-game names:", value=p_name, inline=False)
                    embedVar.set_footer(text="")
                    await message.channel.send(embed=embedVar)
                    ticket_close_timeout[str(message.channel.id)] = False
                    with open('channelids_steam.txt', 'a') as the_file:
                        the_file.write(str(channel_id) + '\n')
                    combi_form_data = merge(form_data, old_form_data)
                    a_file = open("data.json", "w")
                    json.dump(combi_form_data, a_file)
                    a_file.close()

            if str(message.author.id) == "1300850899580747957" and str(message.channel.category.id) in allowed_categories:
                if len(message.embeds) != 0:
                    if "If this is not your " in str(message.embeds[0].title) or "Ticket Control Panel" in str(message.embeds[0].title):
                        emoji_list = ['📌', '🟢', '🔴', '🟠', '🟡', '⚫','🕙', '🆔']
                        for i in emoji_list:
                            await message.add_reaction(i)
                else:
                    pass

            elif "$close " in str(message.content).lower():
                if str(message.author.id) in admin_list.keys():
                    if not form_data[channel_id]['submitted']:
                        close_msg = str(message.content).replace("$close ","")
                        admin = admin_list[str(message.author.id)]
                        form_data[channel_id]['admin'] = admin
                        form_data[channel_id]['close_msg'] = close_msg
                        data = get_values(form_data[channel_id])
                        url = 'https://docs.google.com/forms/d/e/1FAIpQLSfhQRs6_Q7uuPmvVMSArxWsKETPKHYCoklNUTFlwXwRKNwqVA/formResponse'
                        form_data[channel_id]['submitted'] = True
                        send_gform(url, data, message.author)
                        await add_log("Ticket closed and logged in sheets by " + str(message.author))
                
            if "$check" in str(message.content) and str(message.author.id) in admin_list:
                #Check prio
                cf_id = get_cf_from_steam64(form_data[channel_id]['steam64'])
                if str(message.channel.category.id) == "1305326699201691701":
                    server = "487c5364-157b-4824-ac55-21b025f7cec5" #EU1
                elif str(message.channel.category.id) == "1305326716281028650":
                    server = "unused" #EU2
                elif str(message.channel.category.id) == "1305326700200202283":
                    server = "c5738674-bac8-4e04-94e7-bb121198fa2c" #US1
                elif str(message.channel.category.id) == "1305326717271019598":
                    server = "unusedus2" #US2
                else:
                    await message.channel.send(">>> **ERROR** INCORRECT CHANNEL")
                all_dono = check_prio(server)
                found = False
                for count, value in enumerate(all_dono['entries']):
                    if cf_id in value['user']['cftools_id']:
                        found = True
                        expiry = all_dono['entries'][count]['meta']['expiration']
                        if expiry == None:
                            await message.channel.send(">>> User has permanent priority")
                        else:
                            dater = gt(all_dono['entries'][count]['meta']['expiration'])
                            embedVar = discord.Embed(title=form_data[channel_id]['steam64'], description="Requested priority details below", color=0x00ffe5)
                            embedVar.add_field(name="Expiry", value=dater, inline=False)
                            embedVar.add_field(name="Priority Comment", value=all_dono['entries'][count]['meta']['comment'], inline=False)
                            embedVar.set_footer(text="")
                            await message.channel.send(embed=embedVar)
                    else:
                        pass
                if not found:
                    await message.channel.send(">>> User does not have priority, or has not played on this server.")
            
            if "$comp" in str(message.content) and str(message.author.id) in admin_list:
                if str(message.channel.category.id) == "1305326699201691701":
                    server = "487c5364-157b-4824-ac55-21b025f7cec5" #EU1
                elif str(message.channel.category.id) == "1305326716281028650":
                    server = "unused" #EU2
                elif str(message.channel.category.id) == "1305326700200202283":
                    server = "c5738674-bac8-4e04-94e7-bb121198fa2c" #US1
                elif str(message.channel.category.id) == "1305326717271019598":
                    server = "unusedus2" #US2
                else:
                    await message.channel.send(">>> **ERROR** INCORRECT CHANNEL")
                item_list = str(message.content).split()
                item_list.pop(0)
                comp_request[message.channel.id] = {}
                comp_request[message.channel.id]["approved"] = False
                comp_request[message.channel.id]["steam64"] = form_data[channel_id]['steam64']
                comp_request[message.channel.id]["item_list"] = item_list
                comp_request[message.channel.id]["server"] = server
                pretty_item_list = ""
                emoji_list = ['📌', '🟢', '🔴', '🟠', '🟡', '⚫','🕙', '✅', '🕧']
                for item in item_list:
                    pretty_item_list = pretty_item_list + item + "\n"
                await add_log(str(message.author) + "has issued a comp request for: " + pretty_item_list)
                                    

                if check_high_prio(item_list):
                    embedVar = discord.Embed(title="COMP-REQUEST by: " + str(message.author), description=pretty_item_list, color=discord.Color.blue())
                    await message.channel.send(embed=embedVar)
                    await message.channel.send("<@&1305326556368867389> <@&1305326557404856371> <@&1305326558373871737>")
                    await message.delete()
                    for i in admin_list.values():
                        admin_name = re.sub(r'\W+', '', str(i)).lower()
                        if admin_name in str(message.channel.name):
                            new_name = str(message.channel.name).replace(admin_name + "-", "")
                    new_name = str(message.channel.name).lower()
                    new_name = new_name.replace("comp-", "")
                    
                    for i in emoji_list:
                        new_name = new_name.replace(i + "-", "")
                    new_name = "🟠-comp-" + new_name
                    await message.channel.edit(name = new_name)

                #elif mod_role in message.author.roles:
                #    embedVar = discord.Embed(title="COMP-REQUEST by: " + str(message.author), description=pretty_item_list, color=discord.Color.blue())
                #    await message.channel.send(embed=embedVar)
                #    await message.channel.send("<@&1305326556368867389> <@&1305326557404856371> <@&1305326558373871737> <@&1305326559355207690>")
                #    await message.delete()
                #    for i in admin_list.values():
                #        admin_name = re.sub(r'\W+', '', str(i)).lower()
                #        if admin_name in str(message.channel.name):
                #            new_name = str(message.channel.name).replace(admin_name + "-", "")
                #    new_name = str(message.channel.name).lower()
                #    new_name = new_name.replace("comp-", "")
                #    for i in emoji_list:
                #        new_name = new_name.replace(i + "-", "")
                #    new_name = "🔴-comp-" + new_name
                #    await message.channel.edit(name = new_name)

                else:
                    comp_request[message.channel.id]["approved"] = True
                    #comp_items(item_list, form_data[channel_id]['steam64'], server)
                    #embedVar = discord.Embed(title="The following items have been comp'd by: " + str(message.author), description=pretty_item_list, color=discord.Color.blue())
                    await message.channel.send("<@"+form_data[channel_id]['discord_id']+">")
                    embed_title = "Your comp has been approved."
                    embed_desc = "Follow the below instructions to receive your gear"
                    embedVar = discord.Embed(title=embed_title, description=embed_desc, color=discord.Color.blue())
                    embedVar.add_field(name="Be Online and Be Safe", value="Before completing this action make sure you are ONLINE and in a SAFE PLACE", inline=False)
                    embedVar.add_field(name="Once you are ready", value="Type in this channel with \"I AM IN-GAME AND SAFE\" (case sensitive no quotes)", inline=False)
                    embedVar.add_field(name="What will happen?", value="The gear you have been comp'd will spawn at your feet.", inline=False)
                    embedVar.add_field(name="Disclaimer", value="If you accept the comp by typing \"I AM IN-GAME AND SAFE\" and you are offline, unsafe etc - staff are not responsible and will not comp you again", inline=False)
                    await message.channel.send(embed=embedVar)
                    for i in admin_list.values():
                        admin_name = re.sub(r'\W+', '', str(i)).lower()
                        if admin_name in str(message.channel.name):
                            new_name = str(message.channel.name).replace(admin_name + "-", "")
                    new_name = str(message.channel.name).lower()
                    new_name = new_name.replace("comp-", "")
                    for i in emoji_list:
                        new_name = new_name.replace(i + "-", "")
                    new_name = "🕧-comp-" + new_name
                    await message.channel.edit(name = new_name)
                    await message.delete()

            if "I AM IN-GAME AND SAFE" in str(message.content) and comp_request[message.channel.id]["approved"] == True and str(message.author.id) not in admin_list:
                item_list = comp_request[message.channel.id]["item_list"]
                steam64 = comp_request[message.channel.id]["steam64"]
                server = comp_request[message.channel.id]["server"]
                comp_items(item_list, form_data[channel_id]['steam64'], server)
                for i in admin_list.values():
                    admin_name = re.sub(r'\W+', '', str(i)).lower()
                    if admin_name in str(message.channel.name):
                        new_name = str(message.channel.name).replace(admin_name + "-", "")
                comp_request[message.channel.id]["approved"] = False
                pretty_item_list = ""
                for item in item_list:
                    pretty_item_list = pretty_item_list + item + "\n"
                embedVar = discord.Embed(title="The following items have been accepted as compensation by: " + str(message.author), description=pretty_item_list, color=discord.Color.blue())
                await message.channel.send(embed=embedVar)
                new_name = str(message.channel.name).lower()
                new_name = new_name.replace("comp-", "")
                emoji_list = ['📌', '🟢', '🔴', '🟠', '🟡', '⚫','🕙', '✅', '🕧']
                for i in emoji_list:
                    new_name = new_name.replace(i + "-", "")
                new_name = "✅-comp-" + new_name
                await message.channel.edit(name = new_name)

            if message.author.id == 1300850899580747957 and "COMP-REQUEST" in str(message.embeds[0].title):
                emoji_list = ['✅', '❌']
                for i in emoji_list:
                    await message.add_reaction(i)

        #elif "980550532198457424" in str(message.channel.id) and "$countingstats" in str(message.content):
        #     await message.delete()
        #     author_id = str(message.author.id)
        #     with open('countingdb.json', 'r') as thefile:
        #         userdb = json.loads(thefile.read())
        #         thefile.close()

        #     split_str = str(message.content).split()
        #     if len(split_str) == 2:
        #         split_str[1] = re.sub(r'\W+', '', split_str[1])
        #         guild = client.get_guild(1282699130363445380)
        #         requested_user = guild.get_member(int(split_str[1]))
        #         embedVar = discord.Embed(title=requested_user.name, color=0xe4b400)
        #         points = userdb[split_str[1]]["score"]
        #         highest = userdb[split_str[1]]["highest_correct"]
        #         streak_killer = userdb[split_str[1]]["highest_streak"]
        #         streak_killer_count = userdb[split_str[1]]["streak_kill_count"]
        #     else:
        #         embedVar = discord.Embed(title=message.author.name, color=0xe4b400)
        #         points = userdb[author_id]["score"]
        #         highest = userdb[author_id]["highest_correct"]
        #         streak_killer = userdb[author_id]["highest_streak"]
        #         streak_killer_count = userdb[author_id]["streak_kill_count"]
            
        #     embedVar.add_field(name="Total points:", value=points, inline=False)
        #     embedVar.add_field(name="Highest valid number:", value=highest, inline=False)
        #     embedVar.add_field(name="Highest streak killed:", value=streak_killer, inline=False)
        #     embedVar.add_field(name="Number of streaks ruined:", value=streak_killer_count, inline=False)
        #     embedVar.set_footer(text="Type $countingstats to see your score")
        #     await message.channel.send(embed=embedVar)

        # elif "$setslowmode" in str(message.content) and str(message.author.id) == "213025853708304384":
        #     split_str = str(message.content).split()
        #     seconds = split_str[1]
        #     guild = client.get_guild(1282699130363445380)
        #     channel = client.get_channel(980543694061043732)
        #     await channel.edit(slowmode_delay=seconds)


        # elif "980550532198457424" in str(message.channel.id) and "$shield" in str(message.content):
        #     name, discriminator = str(message.author).split('#')
        #     user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        #     guild = client.get_guild(1282699130363445380)
        #     credit_role = discord.utils.get(guild.roles, id=938384994332712990)
        #     channel = client.get_channel(980543694061043732)
        #     twofifty_role = discord.utils.get(guild.roles, id=937729784346210304)
        #     if credit_role in user.roles:
        #         await user.remove_roles(credit_role)
        #         member_role = discord.utils.get(user.guild.roles, id=824305844451540993)
        #         overwrite = discord.PermissionOverwrite()
        #         overwrite.send_messages = False
        #         overwrite.read_messages = True
        #         await channel.set_permissions(member_role, overwrite=overwrite)
        #         overwrite.send_messages = True
        #         overwrite.read_messages = True
        #         await channel.set_permissions(twofifty_role, overwrite=overwrite)
        #         embedVar = discord.Embed(title="Shield Activated", description="Activated by: " + str(message.author), color=0xe4b400)
        #         embedVar.add_field(name="Most users cannot type in the channel now", value="Only members with the <@&937729784346210304> rank or above can type for 60 seconds")
        #         embedVar.set_thumbnail(url="https://www.pngrepo.com/png/320445/512/bordered-shield.png")
        #         await message.channel.send(embed=embedVar)
        #         await asyncio.sleep(60)
        #         overwrite.send_messages = True
        #         overwrite.read_messages = True
        #         await channel.set_permissions(member_role, overwrite=overwrite)
        #         overwrite.send_messages = False
        #         overwrite.read_messages = True
        #         await channel.set_permissions(twofifty_role, overwrite=overwrite)
        #         embedVar = discord.Embed(title="Shield Deactivated", description="Originally activated by: " + str(message.author), color=0xffffff)
        #         embedVar.add_field(name="Full access to channel restored", value="All members of the discord can type in <#980543694061043732> again now")
        #         embedVar.set_thumbnail(url="https://www.pngrepo.com/png/320445/512/bordered-shield.png")
        #         await message.channel.send(embed=embedVar)
        #     else:
        #         embedVar = discord.Embed(title="No shield Credits Available", description="Requested by: " + str(message.author), color=0xff0000)
        #         embedVar.set_thumbnail(url="https://www.pngrepo.com/png/320445/512/bordered-shield.png")
        #         await message.channel.send(embed=embedVar)

        # elif "980550532198457424" in str(message.channel.id) and "$w2n" in str(message.content):
        #     split_string = str(message.content).split()
        #     split_string.pop(0)
        #     content = ' '.join(split_string)
        #     await message.delete()
        #     try:
        #         if str(w2n.word_to_num(str(content))).isnumeric():
        #             embedVar = discord.Embed(title=content, description="Requested by: " + str(message.author), color=0x00ff00)
        #             embedVar.add_field(name="This is a valid entry equalling", value="`"+str(w2n.word_to_num(str(content)))+"`")
        #             embedVar.set_footer(text="command: `$w2n`")
        #             await message.channel.send(embed=embedVar)
        #         else:
        #             embedVar = discord.Embed(title=content, description="Requested by: " + str(message.author), color=0xff0000)
        #             embedVar.add_field(name="This is an invalid entry", value=content)
        #             embedVar.set_footer(text="command: `$w2n`")
        #             await message.channel.send(embed=embedVar)
        #     except:
        #         embedVar = discord.Embed(title=content, description="Requested by: " + str(message.author), color=0xff0000)
        #         embedVar.add_field(name="This is an invalid entry", value=content)
        #         embedVar.set_footer(text="command: `$w2n`")
        #         await message.channel.send(embed=embedVar)
                
                

        #elif "soup" in str(message.content).lower():
        #    if not message.channel.id == 1305326901388382242:
        #        await add_log(str(message.author) + " in " + str(message.channel) + " has SOUP")
        #    emoji_list = ['🇸', '🇴', '🇺', '🇵','🍲']
        #    for i in emoji_list:
        #        await message.add_reaction(i)

        elif "audemars" in str(message.content).lower():
            if not message.channel.id == 1305326901388382242:
                await add_log(str(message.author) + " in " + str(message.channel) + " is NOOB")
            emoji_list = ['🇳', '🇴', '🅾️', '🅱️','💀']
            for i in emoji_list:
                await message.add_reaction(i)

        elif "$updatestaff" in str(message.content).lower():
            members, json_admin_list = get_role_users(message)
            admin_list = json.loads(json_admin_list)
            pretty_admin_list = ""
            for admin in admin_list.values():
                pretty_admin_list = pretty_admin_list + admin + "\n"
            pretty_json = json.dumps(json_admin_list, sort_keys=True, indent=4)
            embedVar = discord.Embed(title="STAFF LIST", description=pretty_admin_list, color=discord.Color.blue())
            #embedVar.add_description(name="Discord ID : Display Name", value=json.dumps(json_admin_list, sort_keys=True, indent=4), inline=False)
            embedVar.set_footer(text="")
            await message.channel.send(embed=embedVar)
            
        # elif "928518517010096128" in str(message.channel.id):
        #     if "1300850899580747957" in str(message.author.id):
        #         await message.add_reaction('✅')
        #     else:
        #         try:
        #             await message.channel.send(str(int(message.content)+randrange(0, 7)))
        #         except:
        #             pass

        # if "937636210095054898" in str(message.channel.id) and str(937678659374952568) not in str(message.id) and str(message.author.id) == "1":
        #     with open('current_number.json') as thefile:
        #         last_number = json.load(thefile)
        #         thefile.close()

        #     with open('highest_number.json') as thefile:
        #         highest_number = json.load(thefile)
        #         thefile.close()

        #     if message.author.id != 1300850899580747957:
        #         await (message.delete())
            
        #     else:
        #         with open('last_count_msg_id.txt', 'r') as thefile:
        #             old_msg_id = thefile.read()
        #             thefile.close()
        #         with open('last_count_msg_id.txt', 'w') as thefile:
        #             thefile.write(str(message.id))
        #             thefile.close()
        #         channel = client.get_channel(937636210095054898)
        #         to_delete = await channel.fetch_message(old_msg_id)
        #         await to_delete.delete()
                

        #     if str(message.content).isnumeric():
        #         number = int(message.content)
        #         current_number = {
        #                 "author": str(message.author),
        #                 "number": number
        #             }
        #         if str(message.author) in last_number["author"]:
        #             pass

        #         elif number == last_number["number"]+1:

        #             if last_number["number"] > 490:
        #                 allowed_mentions = discord.AllowedMentions(everyone = True)
        #                 channel = client.get_channel(935827601405141002)
        #                 await channel.send(content = "@everyone", allowed_mentions = allowed_mentions)
        #                 await channel.send("<#937636210095054898> is about to hit 500 - join in for free priority or ruin it for banter")

        #             if last_number["number"] > 10:
        #                 #10+
        #                 try:
        #                     name, discriminator = last_number["author"].split('#')
        #                     user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        #                     guild = client.get_guild(755342613283864577)
        #                     record_role = discord.utils.get(guild.roles, id=937732431971254352)
        #                     await user.add_roles(record_role)
        #                 except:
        #                     pass

        #             if last_number["number"] > 50:
        #                 #50+
        #                 try:
        #                     name, discriminator = last_number["author"].split('#')
        #                     user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        #                     guild = client.get_guild(755342613283864577)
        #                     record_role = discord.utils.get(guild.roles, id=937729481072857138)
        #                     await user.add_roles(record_role)
        #                 except:
        #                     pass

        #             if last_number["number"] > 100:
        #                 #100+
        #                 try:
        #                     name, discriminator = last_number["author"].split('#')
        #                     user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        #                     guild = client.get_guild(755342613283864577)
        #                     record_role = discord.utils.get(guild.roles, id=937729669464215582)
        #                     await user.add_roles(record_role)
        #                 except:
        #                     pass

        #             if last_number["number"] > 250:
        #                 #C250+
        #                 try:
        #                     name, discriminator = last_number["author"].split('#')
        #                     user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        #                     guild = client.get_guild(937729784346210304)
        #                     record_role = discord.utils.get(guild.roles, id=937729784346210304)
        #                     await user.add_roles(record_role)
        #                 except:
        #                     pass

        #             if last_number["number"] > 500:
        #                 #500+
        #                 try:
        #                     name, discriminator = last_number["author"].split('#')
        #                     user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        #                     guild = client.get_guild(755342613283864577)
        #                     record_role = discord.utils.get(guild.roles, id=937729941720662066)
        #                     await user.add_roles(record_role)
        #                 except:
        #                     pass
        #             with open('current_number.json', 'w') as thefile:
        #                 thefile.write(json.dumps(current_number))
        #                 thefile.close()
        #             math_string = generate_math_problem(number+1)
        #             embedVar = discord.Embed(title=math_string, description="Solve & enter the math problem if you are not sure what number is next (the solution is the number you should enter, NOT the number prior).", color=0x00ffe5)
        #             embedVar.add_field(name="Last number by:", value="<@"+str(message.author.id)+">", inline=False)
        #             #embedVar = discord.Embed(title=math_string, description="Last number by: <@"+str(message.author.id)+">", color=0x00ffe5)
        #             embedVar.set_footer(text="Current high-score is " + str(highest_number["number"]) + " by: " + highest_number["author"])
        #             await message.channel.send(embed=embedVar)

        #         else:
        #             embedVar = discord.Embed(title=str(message.author.name)+" provided the wrong number ("+str(number)+"). What a stupid cunt.", color=0x00ffe5)
        #             embedVar.add_field(name="The correct number was " + str(last_number["number"]+1), value="Number has been reset to 0, next number is 1", inline=False)
        #             embedVar.set_footer(text="Current high-score is " + str(highest_number["number"]) + " by: " + highest_number["author"])
        #             await message.channel.send(embed=embedVar)


        #             if last_number["number"] > highest_number["number"] and last_number["number"] > 50:
        #                 #Counting record setter role: 937695092284723230
        #                 try:
        #                     name, discriminator = last_number["author"].split('#')
        #                     user = discord.utils.get(message.guild.members, name=name, discriminator=discriminator)
        #                     guild = client.get_guild(755342613283864577)
        #                     record_role = discord.utils.get(guild.roles, id=937695092284723230)
        #                     await user.add_roles(record_role)
        #                 except:
        #                     pass

        #                 with open('highest_number.json', 'w') as thefile:
        #                     thefile.write(json.dumps(last_number))
        #                     thefile.close()

        #             current_number = {
        #                 "author": "",
        #                 "number": 0
        #             }
        #             with open('current_number.json', 'w') as thefile:
        #                 thefile.write(json.dumps(current_number))
        #                 thefile.close()
                    
        #     else:
        #         pass

            # if "1300850899580747957" != str(message.author.id):
            #     channel = client.get_channel(937738749431922718)
            #     await channel.send(str(message.author) + ": " + str(message.content) + "||| ID: " + str(message.author.id))
                
        #elif "stew" in str(message.content).lower():
        #    if not message.channel.id == 1305326901388382242:
        #        await add_log(str(message.author) + " in " + str(message.channel) + " has STEW")
        #    await message.channel.send("Did you mean Soup?")


        elif str(message.channel.id) == "1305326859092889601" and not str(message.author.id) == "1300850899580747957":
            #watch-list
            #known_watchers
            now = datetime.datetime.now()
            watch_str = str(message.content).split()
            if str(watch_str[0]).lower() == "$watch":
                if "cftools" in str(watch_str[1]).lower():
                    cf_id = str(watch_str[1])
                    cf_id = cf_id.split("/profile/")[1]
                    cf_id = cf_id.replace('/', '')
                else:
                    cf_id = get_cf_from_steam64(watch_str[1])
                player = get_player_stats(cf_id)
                watch_str.pop(0)
                watch_str.pop(0)
                reason = " ".join(str(x) for x in watch_str)
                if player["status"] == False:
                    await message.channel.send(">>> Player not found, please enter STEAM64 ID")
                else:
                    if player["status"] == False:
                        p_name = "Player has not played on this server."
                    else:
                        p_name = player[cf_id]["omega"]["name_history"]
                        p_name = ', '.join(p_name)
                    if cf_id not in known_watchers:
                        with open('watchlist.txt', 'a') as the_file:
                            the_file.write(str(cf_id) + '\n')
                        known_watchers.append(cf_id)
                        the_file.close()
                        embedVar = discord.Embed(title=p_name, description="Reported at " + now.strftime("%m/%d/%Y, %H:%M:%S"), color=0x00ffe5)
                        embedVar.add_field(name="Reason", value=str(reason), inline=False)
                        embedVar.add_field(name="Reported by", value=message.author, inline=False)
                        embedVar.add_field(name="CFT Profile", value="https://app.cftools.cloud/profile/" + cf_id, inline=False)
                        embedVar.add_field(name="Is this the first report?", value="YES - FIRST TIME ON LIST", inline=False)
                        embedVar.set_footer(text="")
                        await message.channel.send(embed=embedVar)
                        await message.delete()
                    else:
                        await message.author.send(">>> This user (" + p_name + ") has been reported before. Please investigate further.")
                        embedVar = discord.Embed(title=str(p_name), description="Reported at " + now.strftime("%m/%d/%Y, %H:%M:%S"), color=0x00ffe5)
                        embedVar.add_field(name="Reason", value=str(reason), inline=False)
                        embedVar.add_field(name="Reported by", value=message.author, inline=False)
                        embedVar.add_field(name="CFT Profile", value="https://app.cftools.cloud/profile/" + cf_id, inline=False)
                        embedVar.add_field(name="Is this the first report?", value="NO - PLEASE INVESTIGATE", inline=False)
                        embedVar.set_footer(text="")
                        await message.channel.send(embed=embedVar)
                        await message.delete()
            else:
                if not message.author.id == 1300850899580747957:
                    await message.author.send(">>> =====================================")
                    await message.author.send(">>> Please use the following format in #watch-list `$watch <steam64> <reason>`")
                    await message.author.send(">>> Your original message is below:")
                    await message.author.send(">>> =====================================")
                    await message.author.send(str(message.content))
                    await message.delete()

        elif str(message.channel.id) == "862617931766300673":
            #ban list

            if message.author.id == 1300850899580747957 and "BAN REQUEST: " in str(message.embeds[0].title):
                emoji_list = ['✅', '❌']
                for i in emoji_list:
                    await message.add_reaction(i)
            
            else:
            
                now = datetime.datetime.now()
                ban_str = str(message.content).split()
                if str(ban_str[0]).lower() == "$ban":
                    if "cftools" in str(ban_str[1]).lower():
                        cf_id = str(ban_str[1])
                        cf_id = cf_id.split("/profile/")[1]
                        cf_id = cf_id.replace('/', '')
                    else:
                        cf_id = get_cf_from_steam64(ban_str[1])
                    days = ban_str[2]
                    if days == "0":
                        out_days = "1000 YEARS MUAHAHAHA"
                    else:
                        out_days = days
                    player = get_player_stats(cf_id)
                    ban_str.pop(0)
                    ban_str.pop(0)
                    ban_str.pop(0)
                    reason = " ".join(str(x) for x in ban_str)
                    staff_member = admin_list[str(message.author.id)]
                    if len(reason) > 39:
                        await message.channel.send(">>> Please enter a reason less than 40 characters")
                    else:
                        if player["status"] == False:
                            await message.channel.send(">>> Player not found, please enter STEAM64 ID")
                        else:
                            if player["status"] == False:
                                p_name = "Player has not played on this server."
                            else:
                                p_name = player[cf_id]["omega"]["name_history"]
                                p_name = ', '.join(p_name)
                            if not mod_role in message.author.roles:
                                t_response = ban_player(cf_id, days, reason)
                                embedVar = discord.Embed(title=str(p_name), description="Banned at " + now.strftime("%m/%d/%Y, %H:%M:%S"), color=0x00ffe5)
                                embedVar.add_field(name="Reason", value=str(reason), inline=False)
                                embedVar.add_field(name="Banned by", value=message.author, inline=False)
                                embedVar.add_field(name="Ban Duration", value=out_days + " days", inline=False)
                                embedVar.add_field(name="CFT Profile", value="https://app.cftools.cloud/profile/" + cf_id, inline=False)
                                embedVar.set_footer(text="")
                                await message.delete()
                                await message.channel.send(embed=embedVar)

                                channel = client.get_channel(840225718696673330)
                                await channel.send(cf_id + " got banned via API: " + reason)
                                await add_log("Ban issued for " + cf_id)


                            else:
                                ban_data = {}
                                ban_data[message.id] = {}
                                ban_data[message.id]["cf_id"] = cf_id
                                ban_data[message.id]["days"] = days
                                ban_data[message.id]["reason"] = reason
                                combi_form_data = merge(ban_data, old_ban_data)
                                a_file = open("bans.json", "w")
                                json.dump(combi_form_data, a_file)
                                a_file.close()
                                await message.delete()
                                await message.channel.send("<@&1305326559355207690> <@&1305326559976226929> <@&1305326557404856371>")
                                embedVar = discord.Embed(title="BAN REQUEST: " + str(p_name), description=str(message.id), color=0x00ffe5)
                                embedVar.add_field(name="Ban requested by: ", value=str(message.author), inline=False)
                                embedVar.add_field(name="Reason", value=str(reason), inline=False)
                                embedVar.add_field(name="Ban Duration", value=out_days + " days", inline=False)
                                embedVar.add_field(name="CFT Profile", value="https://app.cftools.cloud/profile/" + cf_id, inline=False)
                                embedVar.set_footer(text="")
                                await message.channel.send(embed=embedVar)
                else:
                    if not message.author.id == 1300850899580747957:
                        await message.author.send(">>> =====================================")
                        await message.author.send(">>> Please use the following format in #bans `$ban <steam64 or CFT> <days> <reason>`")
                        await message.author.send(">>> Your original message is below:")
                        await message.author.send(">>> =====================================")
                        await message.author.send(str(message.content))
                        await message.delete()
                

            
            
        elif str(message.channel.id) == "837673813784395817" and "https://" in str(message.content):
            await message.channel.send(message.embeds[0].description)


        elif str(message.channel.id) == "912764799329402930" and "$check" in str(message.content).lower():
            #Check prio
            verify_str = str(message.content).split()
            cf_id = get_cf_from_steam64(verify_str[2].lower())
            if verify_str[1].lower() == "us1":
                server = "c5738674-bac8-4e04-94e7-bb121198fa2c"
            elif verify_str[1].lower() == "us2":
                server = "unusedus2"
            elif verify_str[1].lower() == "eu1":
                server = "487c5364-157b-4824-ac55-21b025f7cec5"
            elif verify_str[1].lower() == "eu2":
                server = "unused"
            else:
                await message.channel.send(">>> **ERROR** YOU FUCKING DONKEY")
            all_dono = check_prio(server)
            found = False
            for count, value in enumerate(all_dono['entries']):
                if cf_id in value['user']['cftools_id']:
                    found = True
                    expiry = all_dono['entries'][count]['meta']['expiration']
                    if expiry == None:
                        await message.channel.send(">>> User has permanent priority")
                    else:
                        dater = gt(all_dono['entries'][count]['meta']['expiration'])
                        embedVar = discord.Embed(title=verify_str[2].lower(), description="Requested priority details below", color=0x00ffe5)
                        embedVar.add_field(name="Expiry", value=dater, inline=False)
                        embedVar.add_field(name="Priority Comment", value=all_dono['entries'][count]['meta']['comment'], inline=False)
                        embedVar.set_footer(text="")
                        await message.channel.send(embed=embedVar)
                        await message.delete()

                else:
                    pass
            if not found:
                await message.channel.send(">>> User does not have priority, or has not played on this server.")
        
        
        if str(message.channel.category.id) in allowed_categories and message.guild:
            if "$check" in str(message.content).lower():
                if str(message.author.id) in admin_list:
                    await message.delete()
                    verify_str = str(message.content).split()
                    cf_id = get_cf_from_steam64(form_data[channel-id]["steam64"].lower())
                    if verify_str[1].lower() == "us1":
                        server = "c5738674-bac8-4e04-94e7-bb121198fa2c"
                    elif verify_str[1].lower() == "us2":
                        server = "unusedus2"
                    elif verify_str[1].lower() == "eu1":
                        server = "487c5364-157b-4824-ac55-21b025f7cec5"
                    elif verify_str[1].lower() == "eu2":
                        server = "unused"
                    else:
                        await message.channel.send(">>> **ERROR** YOU FUCKING DONKEY")
                    all_dono = check_prio(server)
                    found = False
                    for count, value in enumerate(all_dono['entries']):
                        if cf_id in value['user']['cftools_id']:
                            found = True
                            expiry = all_dono['entries'][count]['meta']['expiration']
                            if expiry == None:
                                await message.channel.send(">>> User has permanent priority")
                            else:
                                dater = gt(all_dono['entries'][count]['meta']['expiration'])
                                embedVar = discord.Embed(title=form_data[channel-id]["steam64"], description="Requested priority details below", color=0x00ffe5)
                                embedVar.add_field(name="Expiry", value=dater, inline=False)
                                embedVar.add_field(name="Priority Comment", value=all_dono['entries'][count]['meta']['comment'], inline=False)
                                embedVar.set_footer(text="")
                                await message.channel.send(embed=embedVar)
                        else:
                            pass
                    if not found:
                        await message.channel.send(">>> User does not have priority, or has not played on this server.")
                else: 
                    await message.channel.send(">>> Nice try. Staff only.")

            if "$verify" in str(message.content).lower():
                if str(message.author.id) in admin_list:
                    await message.delete()
                    verify_str = str(message.content).split()
                    if verify_str[1].lower() == "us1":
                        server = "c5738674-bac8-4e04-94e7-bb121198fa2c"
                    elif verify_str[1].lower() == "us2":
                        server = "unusedus2"
                    elif verify_str[1].lower() == "eu1":
                        server = "487c5364-157b-4824-ac55-21b025f7cec5"
                    elif verify_str[1].lower() == "eu2":
                        server = "unused"
                    else:
                        await message.channel.send(">>> Please enter a valid server ID")
                    staff_member = admin_list[str(message.author.id)]
                    if str(verify_str[2]).isdecimal():
                        days = str(verify_str[2])
                    if len(verify_str) == 4:
                        form_data[channel_id]['steam64'] = verify_str[3].lower()
                        vip_msg = issue_prio(form_data[channel_id]['steam64'], server, days, staff_member)
                        channel = client.get_channel(980547938298249316)
                        await channel.send(form_data[channel_id]['steam64'] + " " + verify_str[1].lower())
                        await add_log("Prio issued, staff: " + staff_member)
                    elif len(verify_str) > 4:
                        for i in range(len(verify_str)-3):
                            vip_msg = issue_prio(verify_str[i+3], server, days, staff_member)        
                            channel = client.get_channel(980547938298249316)
                            await channel.send(form_data[channel_id]['steam64'] + " " + verify_str[1].lower())    
                            await add_log("Prio issued, staff: " + staff_member)
                    else:
                        vip_msg = issue_prio(form_data[channel_id]['steam64'], server, days, staff_member)
                        await add_log("Prio issued, staff: " + staff_member)
                    all_dono = check_prio(server)
                    found = False
                    cf_id = get_cf_from_steam64(form_data[channel_id]['steam64'])
                    for count, value in enumerate(all_dono['entries']):
                        if cf_id in value['user']['cftools_id']:
                            found = True
                            expiry = all_dono['entries'][count]['meta']['expiration']
                            if expiry == None:
                                await message.channel.send(">>> User has permanent priority")
                            else:
                                dater = gt(all_dono['entries'][count]['meta']['expiration'])
                                embedVar = discord.Embed(title="Thank you for your donation", description="Priority queue has been issued on " + verify_str[1].upper() + " for " + days + " days", inline=False, color=0x00ffe5)
                                embedVar.add_field(name="Information", value="Your priority will be applied on server restart.")
                                embedVar.add_field(name="Expiry", value=dater)
                                embedVar.add_field(name="Verification", value="This priority has been verified via the API. No manual check is required.", inline=False)
                                embedVar.add_field(name="VIP Tag", value=vip_msg)
                                embedVar.set_footer(text="")
                                await message.channel.send(embed=embedVar)
                        else:
                            pass
                    if not found:
                        await message.channel.send(">>> User does not have priority, or has not played on this server.")
                    if not form_data[channel_id]['submitted']:
                        admin = admin_list[str(message.author.id)]
                        form_data[channel_id]['admin'] = admin
                        data = get_values_dono(form_data[channel_id])
                        url = 'https://docs.google.com/forms/d/e/1FAIpQLSe2yN1N--Sw3hr0qsnKwrA57iUvCQRQbIlaIj9Jvkvb-YBD1w/formResponse'
                        form_data[channel_id]['submitted'] = True
                        send_gform_dono(url, data, message.author)
                        #send to donation tracker
                        channel = client.get_channel(980547938298249316)
                        await channel.send(form_data[channel_id]['steam64'] + " " + verify_str[1].lower())
                        await add_log("Priority submitted by " + str(message.author))
                else:
                    await message.channel.send(">>> Nice try. Staff only.")
        
        if str(message.channel.id) == "1305326810124390481" or str(message.channel.id) == "1305326811286077440" \
            and str(message.author.id) == "1300850899580747957":
            emoji_list = ['👍', '👎']
            for i in emoji_list:
                await message.add_reaction(i)

        if str(message.channel.id) == "1052678263106981938":
            emoji_list = ['👍']
            for i in emoji_list:
                await message.add_reaction(i)

        if "next shit" in str(message.content).lower() and message.author.id != 1300850899580747957:
            a_date = datetime.datetime.now()
            a_month = dateutil.relativedelta.relativedelta(days=1)
            date_plus_month = a_date + a_month
            expiry = str(date_plus_month)
            await message.reply(str(message.author.display_name) + "'s next shit will be at *" + expiry + '*')

        if "$coord" in str(message.content).lower():
            #await message.channel.send(">>> 1. Go to https://www.izurvive.com/")
            #await message.channel.send(">>> 2. Mouse over the location you want to tell us about")
            #await message.channel.send(">>> 3. With the mouse hovering over the location, hit CTRL and C at the same time on your keyboard")
            #await message.channel.send(">>> 4. This will copy the co-ordinates to your clipboard, please paste them into this ticket chat")
            embed=discord.Embed(title="How to provide your co-ordinates")
            embed.add_field(name="Follow these steps:", value="```1. Go to https://www.izurvive.com/\n\n\
2. Mouse over the location you want to tell us about\n\n\
3. With the mouse hovering over the location, hit CTRL and C at the same time on your keyboard\n\n\
4. This will copy the co-ordinates to your clipboard, please paste them into this ticket chat ```", inline=False)
            embed.set_footer(text="")
            await message.channel.send(embed=embed)

        if "$steam64" in str(message.content).lower():
            # await message.channel.send(">>> 1. Open Steam")
            # await message.channel.send(">>> 2. Click your account at the top right.")
            # await message.channel.send(">>> 3. Click account details.")
            # await message.channel.send(">>> 4. Copy the number under YOUR NAME'S ACCOUNT. It begins with 7656.")
            # await message.channel.send("**Alternative**")
            # await message.channel.send(">>> 1. Open up your Steam client and choose View, then click Settings")
            # await message.channel.send(">>> 2. Choose Interface and check the box that reads, \"Display Steam URL address when available\"")
            # await message.channel.send(">>> 3. Click OK")
            # await message.channel.send(">>> 4. Now click on your Steam Profile Name and select View Profile")
            # await message.channel.send(">>> Your SteamID will be listed in the URL at the top left (it's the really long number at the end.)")
            embed=discord.Embed(title="How to provide your STEAM64 ID")
            embed.add_field(name="Option A", value="```1. Open Steam\n\n\
2. Click your account at the top right.\n\n\
3. Click account details.\n\n\
4. Copy the number under YOUR NAME'S ACCOUNT. It begins with 7656.```", inline=False)
            embed.add_field(name="Option B", value="```1. Open up your Steam client and choose View, then click Settings\n\n\
2. Choose Interface and check the box that reads, \"Display Steam URL address when available\"\n\n\
3. Click OK\n\n\
4. Now click on your Steam Profile Name and select View Profile\n\n\
Your SteamID will be listed in the URL at the top left (it's the really long number at the end.)```", inline=False)
            embed.set_footer(text="")
            await message.channel.send(embed=embed)

        if "$name" in str(message.content).lower():
            await message.delete()
            embed=discord.Embed(title="How to change your in-game name")
            embed.add_field(name="DZSA Launcher", value="```1.) Hit Settings (top right) once launcher is open \n\n\
2.) Look for Ingame Name (halfway down) \n\n\
3.) Change from Survivor ```", inline=False)

            embed.add_field(name="Dayz Vanilla Launcher", value="```1.) Once Launcher is open look for PARAMETERS (left side) \n\n\
2.) Go to Profile Name \n\n\
3.) Change from Survivor```", inline=False)

            embed.add_field(name="Dayz Magic Launcher", value="```1.) Once launcher is open look for Settings (top right) \n\n\
2.) Go to Nickname \n\n\
3.) Change from Survivor```", inline=False)
            embed.set_footer(text="")
            await message.channel.send(embed=embed)

        if message.content.startswith('$anon'):
            allowed_role_id = 'ROLE_ID_HERE'  # Replace with your role ID
            role = discord.utils.get(message.guild.roles, id=1305326653873979484)
            if role and role in message.author.roles:
                # Extract the content after the command
                content = message.content[len('$anon'):].strip()
                if content:
                    await message.delete()
                    await message.channel.send(content)
                else:
                    error_msg = await message.channel.send("Please provide a message to send anonymously. Usage: `$anon <message>`")
                    await asyncio.sleep(5)
                    await error_msg.delete()
                    await message.delete()
            else:
                await message.delete()

        if "$updatesteam" in str(message.content).lower():
            update_str = str(message.content).split()
            dc_steam[discord_id[channel_id]] = update_str[1]
            update_dc_steam(dc_steam)
            await message.channel.send(">>> " + "Steam ID for  <@" + discord_id[channel_id] + "> changed to " + update_str[1])

        #if "weed" in str(message.content).lower() and "mod" in str(message.content).lower():
        #    if str(message.author.id) not in admin_list:
        #        await message.reply("No.")

        if "$stash" in str(message.content).lower() and str(message.author.id) in admin_list:
            stash_str = str(message.content).split()
            if stash_str[1].lower() == "us1":
                server = "c5738674-bac8-4e04-94e7-bb121198fa2c"
            elif stash_str[1].lower() == "us2":
                server = "unusedus2"
            elif stash_str[1].lower() == "eu1":
                server = "487c5364-157b-4824-ac55-21b025f7cec5"
            elif stash_str[1].lower() == "eu2":
                server = "unused"
            if stash_str[2]:
                days = stash_str[2]
            else:
                days = "now"
            response = stash_log(server, days)
            response = response.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '')
            response_list = []
            n = 1000
            for index in range(0, len(response), n):
                response_list.append(response[index : index + n])
            for stash_msg in response_list:
                await message.channel.send("```" + stash_msg + "```")

        if "$remind" in str(message.content).lower() and \
            str(message.channel.category.id) in allowed_categories:
            remind_str = str(message.content).split()
            time_msg = str(remind_str[1])
            time = 60 * int(remind_str[1])
            remind_msg = remind_str[2]
            remind_str.pop(0)
            remind_str.pop(0)
            remind_msg = " ".join(str(x) for x in remind_str)
            user = str(message.author.id)
            user = "<@" + user + ">"
            await message.delete()
            await message.channel.send(">>> " + user + "A reminder has been set for: " + str(time_msg) + " minutes")
            await asyncio.sleep(time)
            await message.channel.send(">>> " + user + "this is your reminder for: " + remind_msg)

        # if  asshole in message.author.roles and not message.author.bot:
        #     emoji_list = ['🇦', '🇷', '🇸', '🇪']
        #     for i in emoji_list:
        #         await message.add_reaction(i)

    

client.run('')