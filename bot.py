import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
import logging
import re
from flask import Flask
from threading import Thread

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('slip_bot')

# --- 1. โหลดค่า Config จาก .env ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
try:
    SLIP_CHANNEL_ID = int(os.getenv("SLIP_CHANNEL_ID"))
    STATUS_CHANNEL_ID = int(os.getenv("STATUS_CHANNEL_ID"))
except (ValueError, TypeError):
    logger.error("❌ ไม่พบ SLIP_CHANNEL_ID หรือ STATUS_CHANNEL_ID ในไฟล์ .env")
    exit()

if not TOKEN:
    logger.error("❌ ไม่พบ DISCORD_TOKEN ใน .env")
    exit()

# --- 2. ตั้งค่า SlipOK API ---
SLIP_API_KEY = os.getenv("SLIP_API_KEY")
SLIP_API_ID = os.getenv("SLIP_API_ID", "55097")
SLIP_API_URL = f"https://api.slipok.com/api/line/apikey/{SLIP_API_ID}"

if not SLIP_API_KEY:
    logger.error("❌ ไม่พบ SLIP_API_KEY ใน .env")
    exit()

# --- ตั้งค่า Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Flask Web Server (สำหรับ Render Web Service) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!", 200

@app.route('/health')
def health():
    return {"status": "healthy", "bot": str(bot.user)}, 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    logger.info(f"Flask server started on port {os.environ.get('PORT', 10000)}")


# --- ฟังก์ชันอัพเดท Status Channel ---
async def update_status_channel(member, months_to_add):
    """
    อัพเดท status channel โดยเพิ่ม ✅ ให้กับข้อความเดิมของ member
    ถ้าไม่มีข้อความเดิมจะสร้างใหม่
    """
    try:
        status_channel = bot.get_channel(STATUS_CHANNEL_ID)
        if not status_channel:
            logger.error(f"❌ ไม่พบ Status Channel ID: {STATUS_CHANNEL_ID}")
            return False

        # ค้นหาข้อความเดิมของ member นี้
        found_message = None
        async for msg in status_channel.history(limit=100):
            if msg.author == bot.user and member.mention in msg.content:
                if msg.content.startswith(f"👤 ผู้ส่ง: {member.mention}"):
                    found_message = msg
                    break

        checkmarks_to_add = "✅ " * months_to_add

        if found_message:
            # แก้ไขข้อความเดิม - เพิ่ม ✅
            old_content = found_message.content
            lines = old_content.split('\n')
            first_line = lines[0]
            new_content = first_line + checkmarks_to_add

            if len(lines) > 1:
                new_content += '\n' + '\n'.join(lines[1:])

            await found_message.edit(content=new_content)
            logger.info(f"✅ อัพเดทข้อความเดิมของ {member} สำเร็จ")
        else:
            # สร้างข้อความใหม่
            await status_channel.send(
                f"👤 ผู้ส่ง: {member.mention} : {checkmarks_to_add}"
            )
            logger.info(f"✅ สร้างข้อความใหม่สำหรับ {member} สำเร็จ")

        return True

    except Exception as e:
        logger.error(f"❌ เกิดข้อผิดพลาดในการอัพเดท Status Channel: {e}")
        return False


@bot.event
async def on_ready():
    logger.info(f"✅ บอทล็อกอินเป็น {bot.user}")
    logger.info(f"👀 กำลังตรวจสอบห้อง ID: {SLIP_CHANNEL_ID}")
    logger.info(f"📊 Status Channel ID: {STATUS_CHANNEL_ID}")
    logger.info(f"🚀 ใช้ SlipOK API: {SLIP_API_URL}")
    logger.info(f"🔑 API Key: {'*' * 8} (hidden for security)")


@bot.command()
@commands.has_permissions(administrator=True)
async def verify(ctx, member: discord.Member, months: int = 1):
    """
    (Admin) เพิ่ม ✅ ให้กับสมาชิกใน Status Channel
    """
    try:
        success = await update_status_channel(member, months)
        if success:
            await ctx.send(f"✅ เพิ่ม {months} เดือนให้ {member.mention} สำเร็จ!")
        else:
            await ctx.send(f"❌ เกิดข้อผิดพลาดในการเพิ่มเดือนให้ {member.mention}")
    except Exception as e:
        logger.error(f"Error in verify command: {e}")
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")


@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(
            "❌ **ไม่พบสมาชิกที่ระบุ**\n\n"
            "**วิธีใช้งาน:**\n"
            "`!verify @username [จำนวนเดือน]`\n\n"
            "**ตัวอย่าง:**\n"
            "• `!verify @Alice 1` - เติมให้ Alice 1 เดือน\n"
            "• `!verify @Bob 3` - เติมให้ Bob 3 เดือน"
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ **ขาดข้อมูลที่จำเป็น**\n\n"
            "**วิธีใช้งาน:**\n"
            "`!verify @username [จำนวนเดือน]`"
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (ต้องเป็น Administrator)")


@bot.command()
@commands.has_permissions(administrator=True)
async def monthly_reset(ctx):
    """
    (Admin) ลด ✅ ของทุกคนใน Status Channel ลง 1 เดือน
    """
    try:
        status_channel = bot.get_channel(STATUS_CHANNEL_ID)
        if not status_channel:
            await ctx.send(f"❌ ไม่พบ Status Channel ID: {STATUS_CHANNEL_ID}")
            return

        confirm_msg = await ctx.send(
            "**คำเตือน: คุณกำลังจะลด ✅ ของทุกคนลง 1 เดือน**"
        )
        await confirm_msg.add_reaction("✅")
        await asyncio.sleep(0.5)  # รอ 0.5 วินาที
        await confirm_msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == ctx.author and
                str(reaction.emoji) in ["✅", "❌"] and
                reaction.message.id == confirm_msg.id
            )

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)

            if str(reaction.emoji) == "❌":
                await ctx.send("❌ ยกเลิกการรีเซ็ตแล้ว")
                return

            processing_msg = await ctx.send("🔄 กำลังประมวลผล...")

            members_data = []

            async for message in status_channel.history(limit=200):
                if message.author == bot.user and message.content.startswith("👤 ผู้ส่ง:"):
                    try:
                        lines = message.content.split('\n')
                        first_line = lines[0]
                        checkmark_count = message.content.count("✅")

                        if '<@' in first_line:
                            member_id_match = re.search(r'<@!?(\d+)>', first_line)
                            if member_id_match:
                                member_id = int(member_id_match.group(1))
                                member = ctx.guild.get_member(member_id)

                                if member:
                                    new_checkmarks = checkmark_count - 1
                                    if new_checkmarks > 0:
                                        members_data.append({
                                            'member': member,
                                            'checkmarks': new_checkmarks
                                        })

                        await message.delete()
                        await asyncio.sleep(0.2)

                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

            if members_data:
                members_data.sort(key=lambda x: x['checkmarks'], reverse=True)

                for data in members_data:
                    member = data['member']
                    checkmarks = "✅ " * data['checkmarks']
                    await status_channel.send(
                        f"👤 ผู้ส่ง: {member.mention} : {checkmarks}"
                    )
                    await asyncio.sleep(0.2)

            total_members = len(members_data)
            result_msg = (
                f"✅ **รีเซ็ตรายเดือนเสร็จสิ้น!** ดำเนินการโดย: {ctx.author.mention}"
            )
            await processing_msg.edit(content=result_msg)
            logger.info(f"Monthly reset: {total_members} members remaining")

        except asyncio.TimeoutError:
            await ctx.send("⏰ หมดเวลา - ยกเลิกการรีเซ็ตแล้ว")

    except Exception as e:
        logger.error(f"Error in monthly_reset: {e}")
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")


@monthly_reset.error
async def monthly_reset_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (ต้องเป็น Administrator)")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.id == SLIP_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type in ['image/png', 'image/jpeg', 'image/jpg']:
                logger.info(f"Processing slip from {message.author}: {attachment.filename}")

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as img_response:
                            if img_response.status != 200:
                                await message.channel.send(f"❌ ไม่สามารถดาวน์โหลดรูปภาพได้")
                                continue
                            image_data = await img_response.read()

                    form = aiohttp.FormData()
                    form.add_field('files', image_data, filename=attachment.filename, content_type=attachment.content_type)
                    form.add_field('log', 'true')

                    headers = {'x-authorization': SLIP_API_KEY}

                    async with aiohttp.ClientSession() as session:
                        async with session.post(SLIP_API_URL, data=form, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            response_text = await response.text()
                            logger.info(f"API Response Status: {response.status}")

                            try:
                                result = await response.json()
                            except Exception as json_error:
                                logger.error(f"JSON Parse Error: {json_error}")
                                await message.channel.send(f"❌ API ตอบกลับไม่ถูกต้อง")
                                continue

                            if response.status == 200 and result.get('success', False):
                                data = result.get('data', {})
                                receiver_name = data.get('receiver', {}).get('displayName', 'ไม่ทราบชื่อ')
                                receiver_account = data.get('receiver', {}).get('account', {}).get('value', 'N/A')
                                sender_name = data.get('sender', {}).get('displayName', 'ไม่ทราบชื่อ')
                                sender_account = data.get('sender', {}).get('account', {}).get('value', 'N/A')
                                amount = data.get('amount', 0)
                                ref = data.get('transRef', 'N/A')
                                date_time = data.get('transDate', '') + ' ' + data.get('transTime', '')

                                months = int(amount // 60)
                                if months < 1:
                                    months = 1

                                checkmarks = "✅ " * months

                                await message.channel.send(
                                    f"✅ **สลิปถูกต้อง**\n"
                                    f"👤 ผู้ส่ง: {message.author.mention}\n\n"
                                    f"💰 จำนวนเงิน: **{amount:,.2f} บาท**\n"
                                    f"📤 ผู้โอน: {sender_name}\n"
                                    f"📥 ผู้รับ: {receiver_name}\n"
                                    f"🔢 Ref: {ref}\n"
                                    f"📅 {date_time}\n\n"
                                    f"📊 จำนวนเดือน: **{months}** {checkmarks}\n\n"
                                    f"🎁 **เติมให้ใคร?**\n"
                                    f"• mention (@) คนที่ต้องการ (ได้ {months} คน)\n"
                                    f"• พิมพ์ `ตัวเอง` เพื่อเติมให้ตัวเอง\n"
                                    f"(60 วินาที)"
                                )

                                def msg_check(m):
                                    return m.author == message.author and m.channel == message.channel

                                try:
                                    user_msg = await bot.wait_for('message', timeout=60.0, check=msg_check)

                                    if user_msg.content.strip().lower() in ['ตัวเอง', 'ตนเอง', 'me']:
                                        success = await update_status_channel(message.author, months)
                                        if success:
                                            await message.channel.send(f"✅ เติมให้ {message.author.mention} สำเร็จ! ({months} เดือน)")

                                    elif len(user_msg.mentions) > 0:
                                        selected_members = user_msg.mentions[:months]

                                        if len(selected_members) == 1:
                                            target = selected_members[0]
                                            success = await update_status_channel(target, months)
                                            if success:
                                                await message.channel.send(
                                                    f"✅ เติมให้ {target.mention} สำเร็จ! ({months} เดือน)\n"
                                                    f"🎁 โดย: {message.author.mention}"
                                                )
                                        else:
                                            success_list = []
                                            for target in selected_members:
                                                success = await update_status_channel(target, 1)
                                                if success:
                                                    success_list.append(target.mention)

                                            if success_list:
                                                await message.channel.send(
                                                    f"✅ เติมให้ {', '.join(success_list)} สำเร็จ!\n"
                                                    f"🎁 โดย: {message.author.mention}"
                                                )
                                    else:
                                        success = await update_status_channel(message.author, months)
                                        if success:
                                            await message.channel.send(f"⚠️ ไม่พบ mention - เติมให้ตัวเองแทน")

                                except asyncio.TimeoutError:
                                    success = await update_status_channel(message.author, months)
                                    if success:
                                        await message.channel.send(f"⏰ หมดเวลา - เติมให้ตัวเองแทน")

                            else:
                                error_message = result.get('message', 'ไม่สามารถตรวจสอบได้')
                                await message.channel.send(f"⚠️ สลิปไม่ผ่าน: {error_message}")

                except asyncio.TimeoutError:
                    await message.channel.send(f"❌ API Timeout")
                except Exception as e:
                    logger.error(f"Error: {e}", exc_info=True)
                    await message.channel.send(f"❌ เกิดข้อผิดพลาด")

            else:
                await message.channel.send(f"⚠️ ไฟล์ `{attachment.filename}` ไม่ใช่รูปภาพที่รองรับ")


if __name__ == "__main__":
    logger.info("🚀 กำลังรันบอท...")
    
    # เช็คว่าอยู่บน Render Web Service หรือไม่
    if os.environ.get('RENDER'):
        logger.info("🌐 ตรวจพบ Render - เปิด Flask server")
        keep_alive()
    
    bot.run(TOKEN)