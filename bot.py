import discord
from discord.ext import commands
from discord import ui, ButtonStyle
from discord import ui, SelectOption
import random
import asyncio
import json
import os
import time

# --- CẤU HÌNH HỆ THỐNG TỐI CAO ---
OWNER_ID = 851328559301656606  # ID Chủ sòng của bạn
TOKEN = os.environ.get('TOKEN')
DB_FILE = "database.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="cgk ", intents=intents, help_command=None)

# --- KHỞI TẠO VÀ QUẢN LÝ DATABASE TOÀN DIỆN ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    
    if uid not in db or not isinstance(db[uid], dict):
        old_balance = db[uid] if (uid in db and isinstance(db[uid], (int, float))) else 50000
        db[uid] = {
            "balance": old_balance,
            "xp": 0,
            "level": 1,
            "last_daily": 0,
            "inventory": {
                "weapons": [],
                "animals": []
            }
        }
        save_db(db)
    else:
        default_keys = {
            "balance": 50000,
            "xp": 0,
            "level": 1,
            "last_daily": 0,
            "inventory": {"weapons": [], "animals": []}
        }
        changed = False
        for key, default_value in default_keys.items():
            if key not in db[uid]:
                db[uid][key] = default_value
                changed = True
        if changed:
            save_db(db)
            
    return db[uid]

def update_user(user_id, key, value, mode="set"):
    get_user(user_id) 
    db = load_db()
    uid = str(user_id)
    if mode == "add":
        db[uid][key] += value
    else:
        db[uid][key] = value
    save_db(db)

# --- SỰ KIỆN TỰ ĐỘNG CÀY XP & CỘNG TIỀN KHI LÊN CẤP ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_data = get_user(message.author.id)
    xp_gain = random.randint(1, 5)
    new_xp = user_data["xp"] + xp_gain
    current_lvl = user_data["level"]
    
    xp_needed = current_lvl * 100
    if new_xp >= xp_needed:
        new_xp -= xp_needed
        current_lvl += 1
        
        update_user(message.author.id, "level", current_lvl)
        level_up_reward = current_lvl * 10000
        update_user(message.author.id, "balance", level_up_reward, mode="add")
        
        await message.channel.send(
            f"🎉 Chúc mừng **{message.author.name}** đã thăng cấp lên **Level {current_lvl}**!\n"
            f"🎁 Bạn nhận được phần thưởng độc quyền: **+{level_up_reward:,}** xu đã được cộng vào ví!"
        )
        
    update_user(message.author.id, "xp", new_xp)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"🎰 SÒNG BÀI ONLINE: Bot {bot.user} đã sẵn sàng hoạt động mượt mà!")

# --- [1] LỆNH ADMIN ĐỘC QUYỀN: BƠM TIỀN ---
@bot.command(name="add")
async def add_money(ctx, member: discord.Member = None, amount: int = None):
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ Bạn không có quyền hạn Nhà Cái tối cao để thực hiện lệnh này!")
        return
    if not member or not amount:
        await ctx.send("❌ Cú pháp: `cgk add @tên_user <số_tiền>`")
        return
    update_user(member.id, "balance", amount, mode="add")
    await ctx.send(f"👑 **Nhà Cái Tối Cao** đã bơm **+{amount:,}** xu vào ví của {member.mention}!")

# --- [2] LỆNH XEM SỐ DƯ & LEVEL ---
@bot.command(name="cash")
async def check_cash(ctx):
    u = get_user(ctx.author.id)
    await ctx.send(f"💳 **{ctx.author.name}** | 💰 Số dư: **{u['balance']:,}** xu | 📊 Level: **{u['level']}** ({u['xp']}/{u['level']*100} XP)")

# --- [3] LỆNH ĐIỂM DANH HÀNG NGÀY ---
@bot.command(name="daily")
async def daily_claim(ctx):
    u = get_user(ctx.author.id)
    now = time.time()
    if now - u["last_daily"] < 86400:
        rem = 86400 - (now - u["last_daily"])
        await ctx.send(f"⏳ Bạn đã điểm danh rồi. Hãy quay lại sau **{int(rem//3600)} giờ {int((rem%3600)//60)} phút**!")
        return
    update_user(ctx.author.id, "balance", 5000, mode="add")
    update_user(ctx.author.id, "last_daily", now)
    await ctx.send(f"🎁 **{ctx.author.name}** vừa nhận thành công **5,000** xu quà điểm danh ngày!")

# --- [4] LỆNH TUNG XU (COINFLIP) ---
@bot.command(name="cf")
async def coinflip(ctx, amount: str = None, choice: str = None):
    if not amount or not choice:
        await ctx.send("❌ Cú pháp: `cgk cf <số_tiền/all> <heads/tails>`")
        return
        
    u = get_user(ctx.author.id)
    if amount.lower() == "all":
        bet = u["balance"]
    else:
        try:
            bet = int(amount)
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ!")
            return

    if bet <= 0 or bet > u["balance"]:
        await ctx.send("❌ Tiền cược không hợp lệ hoặc số dư không đủ!")
        return
        
    choice = choice.lower()
    if choice not in ["heads", "tails", "h", "t", "sấp", "ngửa"]:
        await ctx.send("❌ Vui lòng chọn đúng `heads` hoặc `tails`.")
        return
        
    user_choice = "heads" if choice in ["heads", "h", "sấp"] else "tails"
    
    msg = await ctx.send(
        f"**{ctx.author.name}** spent **{bet:,}** 💵 and chose **{user_choice}**!\n"
        f"The coin spins... 🔄"
    )
    
    await asyncio.sleep(1.0)
    
    result = random.choice(["heads", "tails"])
    res_emoji = "🟢" if result == "heads" else "🟡"
    
    if user_choice == result:
        update_user(ctx.author.id, "balance", bet, mode="add")
        await msg.edit(content=
            f"**{ctx.author.name}** spent **{bet:,}** 💵 and chose **{user_choice}**!\n"
            f"The coin spins... {res_emoji} {result}!\n"
            f"You won {bet:,}!"
        )
    else:
        update_user(ctx.author.id, "balance", -bet, mode="add")
        await msg.edit(content=
            f"**{ctx.author.name}** spent **{bet:,}** 💵 and chose **{user_choice}**!\n"
            f"The coin spins... {res_emoji} {result}!\n"
            f"You lost it all... :c"
        )

# --- [5] LỆNH QUAY HŨ (SLOTS) - CHỈ TRÁI CÂY VÀ KIM CƯƠNG NGUYÊN BẢN ---
@bot.command(name="s")
async def slots(ctx, amount: str = None):
    if not amount:
        await ctx.send("❌ Cú pháp: `cgk s <số_tiền/all>`")
        return
        
    u = get_user(ctx.author.id)
    if amount.lower() == "all":
        bet = u["balance"]
    else:
        try:
            bet = int(amount)
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ!")
            return

    if bet <= 0 or bet > u["balance"]:
        await ctx.send("❌ Số tiền cược không hợp lệ hoặc số dư không đủ!")
        return

    # Danh sách vật phẩm nguyên bản theo ý bạn
    items = ["🍎", "🍇", "🍊", "🥭", "💎"]
    
    multipliers = {
        "🍎": 1,
        "🍇": 2,
        "🍊": 3,
        "🥭": 4,
        "💎": 15
    }
    
    is_win = random.random() < 0.50
    
    if is_win:
        winning_item = random.choice(items)
        r1 = r2 = r3 = winning_item
        
        mul = multipliers[winning_item]
        win_amount = bet * mul
        update_user(ctx.author.id, "balance", win_amount, mode="add")
        
        if winning_item == "💎":
            result_msg = f"and won {win_amount:,} 🎉 🔥 NỔ HŨ THẮNG LỚN CỦA X15! 🔥 🎉"
        else:
            result_msg = f"and won {win_amount:,} (Trúng 3 {winning_item} x{mul}) 🥳"
    else:
        r1, r2, r3 = random.sample(items, 3)
        update_user(ctx.author.id, "balance", -bet, mode="add")
        result_msg = f"and lost {bet:,}"
        
# --- HIỆU ỨNG QUAY QUAY CHUYÊN NGHIỆP ---
    msg = await ctx.send(f"    ___SLOTS___\n  | 🔄 | 🔄 | 🔄 | cgk bet {bet:,}")

    # Chạy vòng lặp để tạo hiệu ứng quay 4 lần
    for i in range(4):
        await asyncio.sleep(0.4)
        # Random các biểu tượng trong lúc quay
        s1, s2, s3 = random.choice(items), random.choice(items), random.choice(items)
        await msg.edit(content=f"    ___SLOTS___\n  | {s1} | {s2} | {s3} | cgk bet {bet:,}")

    # Hiển thị kết quả cuối cùng (kết quả đã tính toán từ trước)
    await asyncio.sleep(0.4)
    await msg.edit(content=
        f"    ___SLOTS___\n"
        f"  | {r1} | {r2} | {r3} | cgk bet {bet:,} {result_msg}"
    )

# --- [6] XÌ DÁCH (BLACKJACK) ---
def get_card():
    return f"{random.choice(['♥️','♦️','♣️','♠️'])}{random.choice(['2','3','4','5','6','7','8','9','10','J','Q','K','A'])}"

def calc_hand(hand):
    val, aces = 0, 0
    for card in hand:
        c = card[2:]
        if c in ['J', 'Q', 'K']: val += 10
        elif c == 'A': aces += 1; val += 11
        else: val += int(c)
    while val > 21 and aces: val -= 10; aces -= 1
    return val

class BJView(discord.ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=45)
        self.ctx = ctx
        self.bet = bet
        self.p = [get_card(), get_card()]
        self.d = [get_card(), get_card()]

    def make_embed(self, final=False):
        emb = discord.Embed(title="🃏 SÒNG BÀI BLACKJACK CGK", color=0x2f3136)
        emb.add_field(name=f"🤖 Nhà cái (" + (str(calc_hand(self.d)) if final else "??") + ")", value=" ".join(self.d) if final else f"{self.d[0]} 🎴", inline=False)
        emb.add_field(name=f"🧑 Bạn ({calc_hand(self.p)})", value=" ".join(self.p), inline=False)
        emb.set_footer(text=f"Tiền cược: {self.bet:,} xu")
        return emb

    @discord.ui.button(label="Bốc Bài (Hit)", style=discord.ButtonStyle.green, emoji="➕")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.p.append(get_card())
        if calc_hand(self.p) > 21:
            update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
            self.clear_items()
            await interaction.response.edit_message(embed=self.make_embed(True), content="💥 **Bạn đã Quắc (Vượt quá 21 điểm)! Nhà cái ăn trọn.**", view=self)
            self.stop()
        else:
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Dằn Bài (Stand)", style=discord.ButtonStyle.red, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.clear_items()
        
        await interaction.response.edit_message(content="🤖 **HÀNH ĐỘNG: LẬT MỞ LÁ BÀI CỦA NHÀ CÁI...**", view=self)
        await asyncio.sleep(0.7)
        await interaction.message.edit(embed=self.make_embed(True))
        await asyncio.sleep(0.7)
        
        while calc_hand(self.d) < 17:
            self.d.append(get_card())
            await interaction.message.edit(embed=self.make_embed(True), content="🤖 *Nhà cái đang rút thêm bài...* ➕")
            await asyncio.sleep(0.8)
            
        p, d = calc_hand(self.p), calc_hand(self.d)
        if d > 21 or p > d:
            update_user(self.ctx.author.id, "balance", self.bet, mode="add")
            msg = f"🏆 **Chúc mừng bạn thắng cuộc! Nhận được +{self.bet:,} xu.**"
        elif p < d:
            update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
            msg = f"💸 **Nhà cái điểm cao hơn! Bạn mất -{self.bet:,} xu.**"
        else:
            msg = "🤝 **Hòa bài! Số tiền cược được hoàn lại.**"
            
        await interaction.message.edit(embed=self.make_embed(True), content=msg, view=self)
        self.stop()

@bot.command(name="bj")
async def blackjack_cmd(ctx, amount: str = None):
    if not amount: 
        return await ctx.send("❌ Cú pháp: `cgk bj <số_tiền/all>`")
        
    u = get_user(ctx.author.id)
    if amount.lower() == "all":
        bet = u["balance"]
    else:
        try:
            bet = int(amount)
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ!")
            return

    if bet <= 0 or bet > u["balance"]: 
        return await ctx.send("❌ Số tiền cược không hợp lệ hoặc ví của bạn không đủ xu!")
        
    view = BJView(ctx, bet)
    await ctx.send(embed=view.make_embed(), view=view)
    
# --- [7] TÀI XỈU ---
@bot.command(name="tx")
async def taixiu(ctx, amount: str, choice: str):
    u = get_user(ctx.author.id)
    try:
        bet = u["balance"] if amount.lower() == "all" else int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk tx <số_tiền> <t/x>`")
    
    user_choice = "tai" if choice.lower() in ["t", "tai"] else "xiu"
    
    # 1. Gửi tin nhắn khởi tạo
    msg = await ctx.send("🎲 **Đang lắc xúc xắc...** 🎲")
    
    # 2. Vòng lặp hiệu ứng lắc (hiển thị số ngẫu nhiên 3 lần)
    for _ in range(3):
        await asyncio.sleep(0.4)
        await msg.edit(content=f"🎲 **Đang lắc...** `[{random.randint(1,6)}] [{random.randint(1,6)}] [{random.randint(1,6)}]`")
    
    # 3. Kết quả thật
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
    total = d1 + d2 + d3
    res = "tai" if total >= 11 else "xiu"
    
    # Kiểm tra nổ hũ (1-1-1 đến 6-6-6)
    is_jackpot = (d1 == d2 == d3)
    
    if user_choice == res:
        win_amt = bet * 10 if is_jackpot else bet
        update_user(ctx.author.id, "balance", win_amt, mode="add")
        jackpot_text = "🎉 **NỔ HŨ X10!** " if is_jackpot else "🎉 **Thắng!** "
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n{jackpot_text} Bạn nhận được {win_amt:,} xu.")
    else:
        update_user(ctx.author.id, "balance", -bet, mode="add")
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n💸 **Thua!** Bạn mất {bet:,} xu.")
        
        
# --- [8] CHẲN LẺ ---  
@bot.command(name="cl")
async def chanle(ctx, amount: str, choice: str):
    u = get_user(ctx.author.id)
    try:
        bet = u["balance"] if amount.lower() == "all" else int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk cl <số_tiền> <c/l>`")
    
    user_choice = "chan" if choice.lower() in ["c", "chan"] else "le"
    
    # 1. Gửi tin nhắn khởi tạo
    msg = await ctx.send("🎲 **Đang tung xúc xắc...** 🎲")
    
    # 2. Vòng lặp hiệu ứng lắc
    for _ in range(3):
        await asyncio.sleep(0.4)
        await msg.edit(content=f"🎲 **Đang tung...** `[{random.randint(1,6)}] [{random.randint(1,6)}] [{random.randint(1,6)}]`")
        
    # 3. Kết quả thật
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
    total = d1 + d2 + d3
    res = "chan" if total % 2 == 0 else "le"
    
    is_jackpot = (d1 == d2 == d3)
    
    if user_choice == res:
        win_amt = bet * 10 if is_jackpot else bet
        update_user(ctx.author.id, "balance", win_amt, mode="add")
        jackpot_text = "🎉 **NỔ HŨ X10!** " if is_jackpot else "🎉 **Thắng!** "
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n{jackpot_text} Bạn nhận được {win_amt:,} xu.")
    else:
        update_user(ctx.author.id, "balance", -bet, mode="add")
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n💸 **Thua!** Bạn mất {bet:,} xu.")
        

# --- LỆNH BÀI CÀO (cào) ---
class CaoView(ui.View):
    def __init__(self, ctx, bet, deck):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.deck = deck
        self.player_hand = []
        self.dealer_hand = [self.deck.pop(), self.deck.pop(), self.deck.pop()]

    @ui.button(label="Rút lá bài", style=ButtonStyle.primary)
    async def draw(self, interaction: discord.Interaction, button: ui.Button):
        card = self.deck.pop()
        self.player_hand.append(card)
        
        if len(self.player_hand) < 3:
            content = f"🃏 Bạn đã rút: `{' '.join(self.player_hand)}`\nTiếp tục bấm nút để bốc thêm!"
            await interaction.response.edit_message(content=content, view=self)
        else:
            button.disabled = True
            p_score = self.calculate_score(self.player_hand)
            d_score = self.calculate_score(self.dealer_hand)
            
            # --- TÍNH TOÁN VÀ GHI SỐ TIỀN THẮNG/THUA ---
            if p_score > d_score:
                update_user(self.ctx.author.id, "balance", self.bet, mode="add")
                res = f"🎉 **Thắng!** Bạn nhận được **{self.bet:,} xu**"
            elif p_score < d_score:
                update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
                res = f"💸 **Thua!** Bạn mất **{self.bet:,} xu**"
            else:
                res = f"🤝 **Hòa!** Không mất xu nào."
                
            final_content = (f"🃏 Bài bạn: `{' '.join(self.player_hand)}` (Điểm: **{p_score}**)\n"
                             f"🃏 Nhà cái: `{' '.join(self.dealer_hand)}` (Điểm: **{d_score}**)\n"
                             f"{res}\n💰 Số dư hiện tại: **{get_user(self.ctx.author.id)['balance']:,} xu**")
            
            await interaction.response.edit_message(content=final_content, view=self)

    def calculate_score(self, hand):
        score = 0
        for card in hand:
            rank = card[:-1]
            if rank in ['J', 'Q', 'K']: score += 10
            elif rank == 'A': score += 1
            else: score += int(rank)
        return score % 10

# Lệnh gọi game
@bot.command(name="cao")
async def baicao(ctx, amount: str):
    u = get_user(ctx.author.id)
    try:
        bet = u["balance"] if amount.lower() == "all" else int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk cao <số_tiền>`")
    
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['♠', '♣', '♦', '♥']
    deck = [r + s for r in ranks for s in suits]
    random.shuffle(deck)
    
    view = CaoView(ctx, bet, deck)
    await ctx.send("🃏 Bấm nút để bốc bài:", view=view)
    
    # --- BẦU CUA ---
class BauCuaSelect(ui.Select):
    def __init__(self):
        options = [SelectOption(label=s, value=s) for s in ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]]
        super().__init__(placeholder="Chọn 1 linh vật để đặt...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id:
            return await interaction.response.send_message("❌ Không phải ván của bạn!", ephemeral=True)
            
        self.view.selected_symbol = self.values[0]
        self.disabled = True # KHÓA MENU SAU KHI CHỌN
        
        # CẬP NHẬT LẠI TIN NHẮN GỐC ĐỂ HIỂN THỊ LỰA CHỌN
        new_content = f"🎲 **Bầu Cua Tôm Cá**\nĐã chốt đặt cửa: **{self.values[0]}**\nBấm nút Lắc để xem kết quả!"
        await interaction.response.edit_message(content=new_content, view=self.view)

class BauCuaView(ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.selected_symbol = None
        self.add_item(BauCuaSelect())

    # --- HÀM KIỂM TRA QUYỀN ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Đây không phải ván của bạn!", ephemeral=True)
            return False
        return True

    @ui.button(label="Lắc Xúc Xắc", style=ButtonStyle.success)
    async def roll(self, interaction: discord.Interaction, button: ui.Button):
        # Kiểm tra nếu chưa chọn thì chặn lại
        if not self.selected_symbol:
            return await interaction.response.send_message("❌ Hãy chọn linh vật trước đã!", ephemeral=True)
            
        button.disabled = True
        
        # CHUYỂN SANG DÙNG follow-up để tránh lỗi trùng lặp
        await interaction.response.defer() # Báo cho Discord biết bot đang xử lý
        
        symbols = ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]
        results = [random.choice(symbols) for _ in range(3)]
        hit_count = results.count(self.selected_symbol)
        
        if hit_count > 0:
            win_amt = self.bet * hit_count
            update_user(self.ctx.author.id, "balance", win_amt, mode="add")
            res = f"🎉 **Chúc mừng!** Ra {hit_count} con {self.selected_symbol}. Thắng **{win_amt:,} xu**"
        else:
            update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
            res = f"💸 **Chia buồn!** Không có {self.selected_symbol}. Bạn mất **{self.bet:,} xu**"
            
        final_content = (f"🎲 Kết quả: **{', '.join(results)}**\n"
                         f"{res}\n💰 Số dư: **{get_user(self.ctx.author.id)['balance']:,} xu**")
        
        # Dùng edit_original_response để cập nhật tin nhắn hiện có mà không gây lỗi
        await interaction.edit_original_response(content=final_content, view=self)

@bot.command(name="bc")
async def baucua(ctx, amount: str):
    u = get_user(ctx.author.id)
    try:
        bet = int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk bau <số_tiền>`")
    
    view = BauCuaView(ctx, bet)
    await ctx.send("🎲 **Bầu Cua Tôm Cá** - Chọn cửa và bấm lắc:", view=view)
    
# --- [9] HỆ THỐNG MỞ HÒM VŨ KHÍ (CRATE) ---
@bot.command(name="crate")
async def open_crate(ctx):
    u = get_user(ctx.author.id)
    if u["balance"] < 10000: 
        return await ctx.send("❌ Bạn cần **10,000** xu để mua và mở Crate vũ khí!")
        
    update_user(ctx.author.id, "balance", -10000, mode="add")
    
    rewards = ["⚔️ Kiếm Rỉ Sét (Thường)", "🏹 Cung Gỗ (Thường)", "🛡️ Khiên Thép (Hiếm)", "🪄 Trượng Ma Thuật (Epic)", "🔱 Rìu Thần Thần Thoại (Legendary)"]
    weights = [50, 30, 14, 5, 1]
    result = random.choices(rewards, weights=weights, k=1)[0]
    
    db = load_db()
    uid = str(ctx.author.id)
    if "weapons" not in db[uid]["inventory"]:
        db[uid]["inventory"]["weapons"] = []
    db[uid]["inventory"]["weapons"].append(result)
    save_db(db)
    
    await ctx.send(f"📦 **{ctx.author.name}** đã chi 10,000 xu khui hòm vũ khí và nhận được: **{result}**!")

# --- [10] HỆ THỐNG MỞ HÒM THÚ CƯNG (LOOTBOX) ---
@bot.command(name="lootbox")
async def open_lootbox(ctx):
    u = get_user(ctx.author.id)
    if u["balance"] < 25000: 
        return await ctx.send("❌ Bạn cần **25,000** xu để mua Siêu Hòm Lootbox Thú Cưng!")
        
    update_user(ctx.author.id, "balance", -25000, mode="add")
    
    rewards = ["🦊 Cáo Lửa", "🐼 Gấu Trúc Thần Kỳ", "🐉 Rồng Con Thượng Cổ"]
    weights = [70, 25, 5]
    result = random.choices(rewards, weights=weights, k=1)[0]
    
    db = load_db()
    uid = str(ctx.author.id)
    if "animals" not in db[uid]["inventory"]:
        db[uid]["inventory"]["animals"] = []
    db[uid]["inventory"]["animals"].append(result)
    save_db(db)
    
    await ctx.send(f"🧰 **{ctx.author.name}** mở Siêu Hòm Lootbox và nhận được Linh Thú: **{result}**!")

# --- [11] ĐẤU TRƯỜNG SINH TỬ THÚ CƯNG (BATTLE) ---
@bot.command(name="battle")
async def pet_battle(ctx):
    u = get_user(ctx.author.id)
    animals = u["inventory"].get("animals", [])
    if not animals: 
        return await ctx.send("❌ Bạn không có thú cưng nào để tham chiến! Hãy mua và mở hòm `cgk lootbox` trước.")
    
    my_pet = animals[0]
    wild_enemies = ["🐗 Lợn Rừng Hung Dữ", "🐺 Sói Xám Đói Khát", "🦁 Sư Tử Đầu Đàn"]
    enemy = random.choice(wild_enemies)
    
    msg = await ctx.send(f"⚔️ **{my_pet}** của bạn đang gầm gừ lao vào đấu trường tỉ thí với **{enemy}**...")
    await asyncio.sleep(1.5)
    
    win = random.choice([True, False])
    if win:
        reward_money = random.randint(3000, 8000)
        reward_xp = random.randint(50, 100)
        update_user(ctx.author.id, "balance", reward_money, mode="add")
        
        db = load_db()
        db[str(ctx.author.id)]["xp"] += reward_xp
        save_db(db)
        
        await msg.edit(content=f"🏆 **{my_pet}** đã hạ gục hoàn toàn {enemy}!\n🎁 Phần thưởng mang về: **+{reward_money:,} xu** và **+{reward_xp} XP** tích lũy.")
    else:
        await msg.edit(content=f"💀 Trận chiến kết thúc quá thảm khốc! **{my_pet}** đã bại trận trước {enemy} và được đưa về trạm y tế dưỡng thương.")

# --- KÍCH HOẠT HỆ THỐNG SÒNG BÀI CASINO ---
bot.run('TOKEN')