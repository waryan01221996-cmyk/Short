import time
import json
import csv
import requests
import urllib3
import warnings
import numpy as np
import telebot
import websocket
import logging
from threading import Thread
from datetime import datetime, date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

# ===================== LOGGING =====================
logging.basicConfig(
    filename="bot_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class VPSScalperV5UpgradedV4:
    def __init__(self):
        # Kredensial langsung tertanam di dalam kode sesuai perintah Anda
        self.TOKEN   = "8950081624:AAGi4nZbdQIvKLQ-uL29frBivQNpAB_RAe8"
        self.CHAT_ID = "5691228728"
        self.bot_telegram = telebot.TeleBot(self.TOKEN)

        self.symbol    = "BTCUSDT"
        self.symbol_ws = "btcusdt"
        self.modal_simulasi = 1058.98       
        self.leverage       = 10            

        # ==================== PARAMETER CONFIG ====================
        self.sl_percentage        = 0.0040  # Jarak Stop Loss awal (0.40%)
        self.tp_percentage        = 0.0060  # Jarak Take Profit awal (0.60%)

        self.trigger_trailing_pct = 0.0050  
        self.lock_profit_pct      = 0.0025  
        self.margin_per_trade     = 0.15    
        self.fee_rate             = 0.0004  
        
        # Parameter Indikator (Timeframe Dikunci ke 1 Menit)
        self.timeframe            = "1m"    
        self.ema_cepat            = 9       
        self.ema_lambat           = 21      
        self.ema_filter           = 200     
        self.vol_periode          = 20      
        
        self.stoch_oversold       = 20      
        self.stoch_overbought     = 80      
        self.BUFFER_MAX           = 240     

        # Kontrol WebSocket Dinamis
        self.ws_app               = None
        self.ws_need_restart      = False

        # Pengaman Risiko Harian
        self.daily_loss_limit_pct = 0.06    
        self.modal_awal_hari  = self.modal_simulasi
        self.tanggal_hari_ini = date.today()
        self.bot_paused       = False

        # Variabel Status Positions
        self.status_posisi       = "KOSONG" 
        self.harga_masuk         = 0.0
        self.harga_tp            = 0.0
        self.harga_sl            = 0.0
        self.harga_likuidasi     = 0.0
        self.active_margin       = 0.0      
        self.position_size_btc   = 0.0      
        self.unrealized_pnl      = 0.0      
        self.roe_percentage      = 0.0      
        
        self.is_trailing_active  = False
        self.harga_step_anchor   = 0.0  
        self.harga_live_terakhir = 0.0
        self.signal_cooldown     = False
        self.waktu_terakhir_close = 0.0     

        self.peak_wallet         = self.modal_simulasi
        self.max_drawdown        = 0.0

        self.history_close  = []
        self.history_volume = []
        self.history_high   = []
        self.history_low    = []

        self.total_trade_hari = 0
        self.win_hari         = 0
        self.loss_hari_count  = 0

        self.init_csv_log()
        self.setup_telegram_commands()
        
        self.notif(
            "🚀 *[BOT V5 SCALPER - OPERATIONAL]*\n"
            f"Sistem Remot Telegram Aktif! (TF LOCK: {self.timeframe})\n"
            f"• SL: {self.sl_percentage * 100:.2f}% | TP: {self.tp_percentage * 100:.2f}%\n"
            f"• Trailing Trigger: {self.trigger_trailing_pct * 100:.2f}% | Lock Profit: {self.lock_profit_pct * 100:.2f}%\n"
            "• Saldo Wallet: ${:,.2f}".format(self.modal_simulasi)
        )

    def init_csv_log(self):
        try:
            with open("trade_log.csv", "x", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Waktu","Arah","Entry","Exit","TP","SL","PnL","Saldo","Alasan"])
        except FileExistsError:
            pass

    def log_trade(self, arah, entry, exit_price, tp, sl, pnl, saldo, alasan):
        try:
            with open("trade_log.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    arah, f"{entry:.2f}", f"{exit_price:.2f}",
                    f"{tp:.2f}", f"{sl:.2f}", f"{pnl:.2f}", f"{saldo:.2f}", alasan
                ])
        except Exception:
            pass

    def notif(self, pesan):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.TOKEN}/sendMessage",
                data={"chat_id": self.CHAT_ID, "text": pesan, "parse_mode": "Markdown"},
                timeout=5
            )
        except Exception:
            pass

    def check_daily_reset(self):
        hari_ini = date.today()
        if hari_ini != self.tanggal_hari_ini:
            self.tanggal_hari_ini = hari_ini
            self.modal_awal_hari = self.modal_simulasi + (self.active_margin if self.status_posisi != "KOSONG" else 0)
            self.total_trade_hari = 0
            self.win_hari = 0
            self.loss_hari_count = 0
            self.bot_paused = False
            self.notif("🔄 *[DAILY SYSTEM RESET]* Statistik performa harian di-reset otomatis!")

    def setup_telegram_commands(self):
        @self.bot_telegram.message_handler(commands=['help', 'start'])
        def send_help(message):
            if str(message.chat.id) != self.CHAT_ID: return
            text = (
                "ℹ️ *PANDUAN NAVIGASI REMOT TELEGRAM V5 (FULL CONTROL)*\n\n"
                "*Informasi & Laporan:*\n"
                "• `/status` - Informasi real-time Akun, ROE%, PNL, & Posisi.\n"
                "• `/log` - Download file berkas laporan `trade_log.csv`.\n"
                "• `/resume` - Aktifkan kembali bot.\n\n"
                "*Pengaturan Kontrol Strategi:*\n"
                "• `/set_ind <cepat> <lambat> <filter>` - Atur EMA (contoh: `/set_ind 9 21 200`)\n"
                "• `/set_stoch <os> <ob>` - Batas Stochastic (contoh: `/set_stoch 20 80`)\n"
                "• `/set_sl <persen>` - Atur jarak Stop Loss (misal: `/set_sl 0.4`)\n"
                "• `/set_tp <persen>` - Atur jarak Take Profit (misal: `/set_tp 0.6`)\n"
                "• `/set_trailing <persen>` - Atur pemicu Trailing\n"
                "• `/set_lock <persen>` - Atur profit terkunci\n"
                "• `/set_leverage <angka>` | `/set_margin <persen>`\n\n"
                "*Eksekusi Darurat:*\n"
                "• `/stop` - Tutup paksa posisi berjalan."
            )
            self.bot_telegram.reply_to(message, text, parse_mode="Markdown")

        @self.bot_telegram.message_handler(commands=['set_ind'])
        def ubah_indikator(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                args = message.text.split()
                cepat = int(args[1])
                lambat = int(args[2])
                filter_ema = int(args[3])
                if 2 <= cepat < lambat < filter_ema <= self.BUFFER_MAX:
                    self.ema_cepat = cepat
                    self.ema_lambat = lambat
                    self.ema_filter = filter_ema
                    self.bot_telegram.reply_to(message, f"⚙️ *[INDIKATOR UPDATED]*\n• EMA Cepat: *{cepat}*\n• EMA Lambat: *{lambat}*\n• EMA Filter: *{filter_ema}*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Format salah. Contoh: `/set_ind 9 21 200`\n(Syarat: Cepat < Lambat < Filter < 240)")

        @self.bot_telegram.message_handler(commands=['set_stoch'])
        def ubah_stoch(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                args = message.text.split()
                os = int(args[1])
                ob = int(args[2])
                if 0 <= os < ob <= 100:
                    self.stoch_oversold = os
                    self.stoch_overbought = ob
                    self.bot_telegram.reply_to(message, f"⚙️ *[STOCHASTIC UPDATED]*\n• Oversold (OS): *{os}*\n• Overbought (OB): *{ob}*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Format salah. Contoh: `/set_stoch 20 80`")

        @self.bot_telegram.message_handler(commands=['resume'])
        def resume_bot(message):
            if str(message.chat.id) != self.CHAT_ID: return
            self.bot_paused = False
            self.modal_awal_hari = self.modal_simulasi + (self.active_margin if self.status_posisi != "KOSONG" else 0)
            self.bot_telegram.reply_to(message, "🟢 *[BOT RESUMED]* Sinyal pemindaian market diaktifkan kembali.")

        @self.bot_telegram.message_handler(commands=['status'])
        def send_status(message):
            if str(message.chat.id) != self.CHAT_ID: return
            
            wallet_total = self.modal_simulasi + (self.active_margin if self.status_posisi != "KOSONG" else 0)
            pnl_hari = wallet_total - self.modal_awal_hari
            winrate  = (self.win_hari / self.total_trade_hari * 100) if self.total_trade_hari > 0 else 0
            
            harga_sekarang = self.harga_live_terakhir if self.harga_live_terakhir > 0 else (self.history_close[-1] if self.history_close else 0.0)

            text = (
                f"📊 *BINANCE FUTURES SYSTEM STATUS*\n"
                f"----------------------------------------\n"
                f"🪙 *Harga Live BTC :* ${harga_sekarang:,.2f}\n"
                f"💰 *Wallet Balance :* ${wallet_total:,.2f}\n"
                f"• PnL Hari Ini   : {'🔴' if pnl_hari < 0 else '🟢'} ${pnl_hari:,.2f}\n"
                f"• Status Kerja   : {'⏸️ PAUSED' if self.bot_paused else '⚙️ RUNNING'}\n"
                f"• Performa Hari  : {self.total_trade_hari} Trade (W:{self.win_hari} L:{self.loss_hari_count}) - Winrate: {winrate:.1f}%\n"
                f"----------------------------------------\n"
                f"⚙️ *Konfigurasi Aktif :*\n"
                f"• TF Running : *{self.timeframe}*\n"
                f"• Rumus EMA  : EMA({self.ema_cepat}) | EMA({self.ema_lambat}) | Filter({self.ema_filter})\n"
                f"• Stoch Bound: OS({self.stoch_oversold}) | OB({self.stoch_overbought})\n"
                f"• Target SL: {self.sl_percentage * 100:.2f}% | Target TP: {self.tp_percentage * 100:.2f}%\n"
                f"• Trailing Trigger: {self.trigger_trailing_pct * 100:.2f}% | Lock: {self.lock_profit_pct * 100:.2f}%\n"
                f"----------------------------------------\n"
                f"📈 *Status Posisi Berjalan:* *{self.status_posisi}*\n"
            )
            
            if self.status_posisi != "KOSONG":
                tanda_pnl = "🟩" if self.unrealized_pnl >= 0 else "🟥"
                text += (
                    f"• Isolated Margin: ${self.active_margin:,.2f} ({self.leverage}x)\n"
                    f"• Entry Price  : ${self.harga_masuk:,.2f}\n"
                    f"• Target TP/SL : ${self.harga_tp:,.2f} / ${self.harga_sl:,.2f}\n"
                    f"{tanda_pnl} *Unrealized PNL:* {self.unrealized_pnl:+.2f} USD ({self.roe_percentage:+.2f}% ROE)"
                )
            else:
                text += "• Tidak ada posisi aktif saat ini."
            self.bot_telegram.reply_to(message, text, parse_mode="Markdown")

        @self.bot_telegram.message_handler(commands=['set_sl'])
        def ubah_sl(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                val = float(message.text.split()[1])
                if 0.01 <= val <= 10.0:
                    self.sl_percentage = val / 100
                    self.bot_telegram.reply_to(message, f"⚙️ *[CONFIG UPDATED]* Jarak Stop Loss diset ke: *{val}%*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Format salah. Contoh: `/set_sl 0.4`")

        @self.bot_telegram.message_handler(commands=['set_tp'])
        def ubah_tp(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                val = float(message.text.split()[1])
                if 0.01 <= val <= 20.0:
                    self.tp_percentage = val / 100
                    self.bot_telegram.reply_to(message, f"⚙️ *[CONFIG UPDATED]* Jarak Take Profit diset ke: *{val}%*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Format salah. Contoh: `/set_tp 0.6`")

        @self.bot_telegram.message_handler(commands=['set_trailing'])
        def ubah_trailing(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                val = float(message.text.split()[1])
                if 0.01 <= val <= 5.0:
                    if (val / 100) < self.lock_profit_pct:
                        self.bot_telegram.reply_to(message, f"⚠️ Gagal! Jarak trailing ({val}%) tidak boleh lebih kecil dari Lock Profit aktif ({self.lock_profit_pct*100:.2f}%)")
                        return
                    self.trigger_trailing_pct = val / 100
                    self.bot_telegram.reply_to(message, f"⚙️ *[CONFIG UPDATED]* Pemicu Trailing Stop diset ke: *{val}%*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Format salah. Contoh: `/set_trailing 0.5`")

        @self.bot_telegram.message_handler(commands=['set_lock'])
        def ubah_lock_profit(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                val = float(message.text.split()[1])
                if 0.00 <= val <= 5.0:
                    if (val / 100) > self.trigger_trailing_pct:
                        self.bot_telegram.reply_to(message, f"⚠️ Gagal! Lock Profit ({val}%) tidak boleh melebihi batas pemicu Trailing ({self.trigger_trailing_pct*100:.2f}%)")
                        return
                    self.lock_profit_pct = val / 100
                    self.bot_telegram.reply_to(message, f"⚙️ *[CONFIG UPDATED]* Lock Profit diset ke: *{val}%*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Format salah. Contoh: `/set_lock 0.25`")

        @self.bot_telegram.message_handler(commands=['set_leverage'])
        def ubah_leverage(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                val = int(message.text.split()[1])
                if 1 <= val <= 125:
                    self.leverage = val
                    self.bot_telegram.reply_to(message, f"⚙️ *[CONFIG UPDATED]* Leverage Binance: *{self.leverage}x*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Nominal leverage tidak valid.")

        @self.bot_telegram.message_handler(commands=['set_margin'])
        def ubah_margin(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                val = float(message.text.split()[1])
                if 1 <= val <= 100:
                    self.margin_per_trade = val / 100
                    self.bot_telegram.reply_to(message, f"⚙️ *[CONFIG UPDATED]* Margin per trade: *{val}%*")
                else: raise ValueError
            except:
                self.bot_telegram.reply_to(message, "⚠️ Persentase tidak valid.")

        @self.bot_telegram.message_handler(commands=['stop'])
        def emergency_stop(message):
            if str(message.chat.id) != self.CHAT_ID: return
            if self.status_posisi == "KOSONG":
                self.bot_telegram.reply_to(message, "⚠️ Tidak ada posisi aktif.")
                return
            
            arah_sebelumnya = self.status_posisi
            self.status_posisi = "KOSONG"
            
            harga_exit = self.harga_live_terakhir if self.harga_live_terakhir > 0 else self.harga_masuk
            close_value = self.position_size_btc * harga_exit
            close_fee = close_value * self.fee_rate
            
            pnl_bersih = self.unrealized_pnl - close_fee
            self.modal_simulasi += (self.active_margin + pnl_bersih)
            self.total_trade_hari += 1
            if pnl_bersih >= 0: 
                self.win_hari += 1
            else: 
                self.loss_hari_count += 1
            
            self.log_trade(arah_sebelumnya, self.harga_masuk, harga_exit, self.harga_tp, self.harga_sl, pnl_bersih, self.modal_simulasi, "Manual Stop")
            
            self.active_margin = 0.0
            self.waktu_terakhir_close = time.time()
            
            text = (
                f"🛑 *[EMERGENCY MARKET CLOSE]*\n"
                f"Posisi {arah_sebelumnya} Ditutup Paksa Via Telegram!\n"
                f"• Exit Price : ${harga_exit:,.2f}\n"
                f"• Net PnL    : {pnl_bersih:+.2f} USD"
            )
            self.bot_telegram.reply_to(message, text, parse_mode="Markdown")

        @self.bot_telegram.message_handler(commands=['log'])
        def kirim_log(message):
            if str(message.chat.id) != self.CHAT_ID: return
            try:
                with open("trade_log.csv", "rb") as f:
                    self.bot_telegram.send_document(self.CHAT_ID, f)
            except:
                self.bot_telegram.reply_to(message, "❌ Log file tidak ditemukan.")

    def ambil_klines(self):
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={self.symbol}&interval={self.timeframe}&limit=240"
            res = requests.get(url, verify=False, timeout=10).json()
            self.history_close  = [float(k[4]) for k in res]
            self.history_high   = [float(k[2]) for k in res]
            self.history_low    = [float(k[3]) for k in res]
            self.history_volume = [float(k[5]) for k in res]
            self.history_close.append(self.history_close[-1])
            self.history_high.append(self.history_high[-1])
            self.history_low.append(self.history_low[-1])
            self.history_volume.append(0.0)
        except Exception as e:
            logging.error(f"Error ambil_klines: {str(e)}")

    def append_candle_closed(self, kline):
        self.history_close[-1]  = float(kline['c'])
        self.history_high[-1]   = float(kline['h'])
        self.history_low[-1]    = float(kline['l'])
        self.history_volume[-1] = float(kline['v'])
        self.history_close.append(float(kline['c']))
        self.history_high.append(float(kline['c']))
        self.history_low.append(float(kline['c']))
        self.history_volume.append(0.0)
        if len(self.history_close) > self.BUFFER_MAX + 1:
            self.history_close.pop(0)
            self.history_high.pop(0)
            self.history_low.pop(0)
            self.history_volume.pop(0)

    def hitung_ema(self, data, periode):
        if len(data) < periode: return None
        alpha = 2 / (periode + 1)
        ema = [np.mean(data[:periode])]
        for price in data[periode:]:
            ema.append((price * alpha) + (ema[-1] * (1 - alpha)))
        return ema[-1]

    def hitung_stochastic(self):
        if len(self.history_close) < 10: return None
        harga = np.array(self.history_close[-10:])
        pk_raw = []
        for i in range(5, len(harga) + 1):
            window = harga[i-5:i]
            low, high = min(window), max(window)
            pk_raw.append(50 if high-low == 0 else ((window[-1]-low)/(high-low))*100)
        return np.mean(pk_raw[-3:]) if len(pk_raw) >= 3 else None

    def proses_trading(self, harga_live, volume_live):
        self.check_daily_reset()
        self.harga_live_terakhir = harga_live

        if self.history_close:
            self.history_close[-1]  = harga_live
            self.history_volume[-1] = volume_live
            if harga_live > self.history_high[-1]: self.history_high[-1] = harga_live
            if harga_live < self.history_low[-1]: self.history_low[-1] = harga_live

        wallet_total_live = self.modal_simulasi + (self.active_margin if self.status_posisi != "KOSONG" else 0)
        loss_hari_ini_pct = (self.modal_awal_hari - wallet_total_live) / self.modal_awal_hari
        if loss_hari_ini_pct >= self.daily_loss_limit_pct and not self.bot_paused:
            self.bot_paused = True
            self.notif(f"⚠️ *[RISK PAUSE ACTIVE]* Ekuitas drop hingga {loss_hari_ini_pct*100:.2f}%. Pembukaan posisi baru dihentikan sementara!")

        if self.status_posisi != "KOSONG":
            nilai_kontrak_live = self.position_size_btc * harga_live
            nilai_kontrak_awal = self.position_size_btc * self.harga_masuk
            
            if self.status_posisi == "LONG":
                self.unrealized_pnl = nilai_kontrak_live - nilai_kontrak_awal
            elif self.status_posisi == "SHORT":
                self.unrealized_pnl = nilai_kontrak_awal - nilai_kontrak_live
                
            self.roe_percentage = (self.unrealized_pnl / self.active_margin) * 100
            
            if (self.status_posisi == "LONG" and harga_live <= self.harga_likuidasi) or \
               (self.status_posisi == "SHORT" and harga_live >= self.harga_likuidasi):
                
                arah_sebelumnya = self.status_posisi
                self.status_posisi = "KOSONG"
                
                self.total_trade_hari += 1
                self.loss_hari_count += 1
                
                self.log_trade(arah_sebelumnya, self.harga_masuk, harga_live, self.harga_tp, self.harga_sl, -self.active_margin, self.modal_simulasi, "LIQUIDATED")
                self.notif(f"☠️ *[LIQUIDATION CALL]* Harga menyentuh Liq Price pada ${harga_live:,.2f}!")
                self.active_margin = 0.0
                self.waktu_terakhir_close = time.time()
                return
        else:
            self.unrealized_pnl = 0.0
            self.roe_percentage = 0.0

        if wallet_total_live > self.peak_wallet:
            self.peak_wallet = wallet_total_live
        
        drawdown_saat_ini = ((self.peak_wallet - wallet_total_live) / self.peak_wallet) * 100
        if drawdown_saat_ini > self.max_drawdown:
            self.max_drawdown = drawdown_saat_ini

        if self.bot_paused and self.status_posisi == "KOSONG": return
        if len(self.history_close) < self.BUFFER_MAX: return

        ema_cepat  = self.hitung_ema(self.history_close[:-1], self.ema_cepat)
        ema_lambat = self.hitung_ema(self.history_close[:-1], self.ema_lambat)
        ema_filter = self.hitung_ema(self.history_close[:-1], self.ema_filter) 
        stoch_k    = self.hitung_stochastic()
        avg_volume = np.mean(self.history_volume[-(self.vol_periode+1):-1]) if len(self.history_volume) >= self.vol_periode else None

        if None in [ema_cepat, ema_lambat, ema_filter, stoch_k, avg_volume]: return

        # ==================== LOGIKA OPEN POSISI ====================
        if self.status_posisi == "KOSONG" and not self.signal_cooldown:
            temp_margin = self.modal_simulasi * self.margin_per_trade
            notional_value = temp_margin * self.leverage
            open_fee = notional_value * self.fee_rate
            
            if self.modal_simulasi < (temp_margin + open_fee): return

            is_volume_valid = True

            # LONG ENTRY
            if (harga_live > ema_cepat and ema_cepat > ema_lambat and harga_live > ema_filter and stoch_k <= self.stoch_oversold and is_volume_valid):
                
                self.modal_simulasi -= (temp_margin + open_fee)
                self.active_margin = temp_margin
                self.position_size_btc = notional_value / harga_live
                self.harga_masuk        = harga_live
                
                self.harga_sl           = harga_live * (1.0 - self.sl_percentage)
                self.harga_tp           = harga_live * (1.0 + self.tp_percentage)
                self.harga_likuidasi    = self.harga_masuk * (1 - (1 / self.leverage) + 0.004)
                
                self.status_posisi      = "LONG"
                self.signal_cooldown    = True
                self.is_trailing_active = False
                self.notif(f"🟩 *[OPEN LONG]*\n• Entry Price : ${self.harga_masuk:,.2f}\n• Stop Loss   : ${self.harga_sl:,.2f}\n• Take Profit  : ${self.harga_tp:,.2f}")

            # SHORT ENTRY
            elif (harga_live < ema_cepat and ema_cepat < ema_lambat and harga_live < ema_filter and stoch_k >= self.stoch_overbought and is_volume_valid):
                
                self.modal_simulasi -= (temp_margin + open_fee)
                self.active_margin = temp_margin
                self.position_size_btc = notional_value / harga_live
                self.harga_masuk        = harga_live
                
                self.harga_sl           = harga_live * (1.0 + self.sl_percentage)
                self.harga_tp           = harga_live * (1.0 - self.tp_percentage)
                self.harga_likuidasi    = self.harga_masuk * (1 + (1 / self.leverage) - 0.004)
                
                self.status_posisi      = "SHORT"
                self.signal_cooldown    = True
                self.is_trailing_active = False
                self.notif(f"🟥 *[OPEN SHORT]*\n• Entry Price : ${self.harga_masuk:,.2f}\n• Stop Loss   : ${self.harga_sl:,.2f}\n• Take Profit  : ${self.harga_tp:,.2f}")

        # ==================== LOGIKA TRAILING & EKSEKUSI EXIT ====================
        elif self.status_posisi in ["LONG", "SHORT"]:
            self.signal_cooldown = False
            close_trigger = False
            alasan = ""

            if self.status_posisi == "LONG":
                if not self.is_trailing_active and harga_live >= self.harga_masuk * (1 + self.trigger_trailing_pct):
                    self.harga_sl = self.harga_masuk * (1 + self.lock_profit_pct)
                    self.is_trailing_active = True
                    self.harga_step_anchor = harga_live
                    self.notif(f"🔒 *[TRAILING LONG AKTIF]* SL awal dikunci: ${self.harga_sl:,.2f}")

                if self.is_trailing_active:
                    if harga_live > self.harga_step_anchor:
                        selisih_naik = harga_live - self.harga_step_anchor
                        self.harga_sl += selisih_naik
                        self.harga_tp += selisih_naik
                        self.harga_step_anchor = harga_live
                        self.notif(f"🚀 *[BRACKET LONG SCALING UP]*\n• TP Baru : ${self.harga_tp:,.2f}\n• SL Baru: ${self.harga_sl:,.2f}")

                if harga_live >= self.harga_tp:
                    close_trigger = True
                    alasan = "TP Hit"
                elif harga_live <= self.harga_sl:
                    close_trigger = True
                    alasan = "Trailing Hit" if self.is_trailing_active else "SL Hit"

            elif self.status_posisi == "SHORT":
                if not self.is_trailing_active and harga_live <= self.harga_masuk * (1 - self.trigger_trailing_pct):
                    self.harga_sl = self.harga_masuk * (1 - self.lock_profit_pct)
                    self.is_trailing_active = True
                    self.harga_step_anchor = harga_live
                    self.notif(f"🔒 *[TRAILING SHORT AKTIF]* SL awal dikunci: ${self.harga_sl:,.2f}")

                if self.is_trailing_active:
                    if harga_live < self.harga_step_anchor:
                        selisih_turun = self.harga_step_anchor - harga_live
                        self.harga_sl -= selisih_turun
                        self.harga_tp -= selisih_turun
                        self.harga_step_anchor = harga_live
                        self.notif(f"🚀 *[BRACKET SHORT SCALING DOWN]*\n• TP Baru : ${self.harga_tp:,.2f}\n• SL Baru: ${self.harga_sl:,.2f}")

                if harga_live <= self.harga_tp:
                    close_trigger = True
                    alasan = "TP Hit"
                elif harga_live >= self.harga_sl:
                    close_trigger = True
                    alasan = "Trailing Hit" if self.is_trailing_active else "SL Hit"

            if close_trigger:
                arah_sebelumnya = self.status_posisi
                
                close_fee = (self.position_size_btc * harga_live) * self.fee_rate
                pnl_bersih = self.unrealized_pnl - close_fee
                
                self.modal_simulasi += (self.active_margin + pnl_bersih)
                self.total_trade_hari += 1
                
                if pnl_bersih >= 0: 
                    self.win_hari += 1
                else: 
                    self.loss_hari_count += 1
                
                self.log_trade(arah_sebelumnya, self.harga_masuk, harga_live, self.harga_tp, self.harga_sl, pnl_bersih, self.modal_simulasi, alasan)
                self.notif(f"{'✅' if pnl_bersih >= 0 else '❌'} *[{alasan.upper()} - {arah_sebelumnya}]*\n• Exit Price : ${harga_live:,.2f}\n• Net PnL    : {pnl_bersih:+.2f} USD")
                
                self.active_margin = 0.0
                self.waktu_terakhir_close = time.time()

                # ==================== STOP AND REVERSE LOGIC ====================
                if alasan == "SL Hit" and not self.bot_paused:
                    self.notif("🔄 *[STOP & REVERSE]* Mengambil posisi kebalikan karena SL terkena hit!")
                    
                    temp_margin = self.modal_simulasi * self.margin_per_trade
                    notional_value = temp_margin * self.leverage
                    open_fee = notional_value * self.fee_rate
                    
                    if self.modal_simulasi >= (temp_margin + open_fee):
                        self.modal_simulasi -= (temp_margin + open_fee)
                        self.active_margin = temp_margin
                        self.position_size_btc = notional_value / harga_live
                        self.harga_masuk = harga_live
                        self.is_trailing_active = False
                        
                        if arah_sebelumnya == "LONG":
                            self.status_posisi   = "SHORT"
                            self.harga_sl        = harga_live * (1.0 + self.sl_percentage)
                            self.harga_tp        = harga_live * (1.0 - self.tp_percentage)
                            self.harga_likuidasi = self.harga_masuk * (1 + (1 / self.leverage) - 0.004)
                            self.notif(f"🟥 *[REVERSE TO SHORT]*\n• Entry Price : ${self.harga_masuk:,.2f}\n• Stop Loss   : ${self.harga_sl:,.2f}\n• Take Profit  : ${self.harga_tp:,.2f}")
                        
                        elif arah_sebelumnya == "SHORT":
                            self.status_posisi   = "LONG"
                            self.harga_sl        = harga_live * (1.0 - self.sl_percentage)
                            self.harga_tp        = harga_live * (1.0 + self.tp_percentage)
                            self.harga_likuidasi = self.harga_masuk * (1 - (1 / self.leverage) + 0.004)
                            self.notif(f"🟩 *[REVERSE TO LONG]*\n• Entry Price : ${self.harga_masuk:,.2f}\n• Stop Loss   : ${self.harga_sl:,.2f}\n• Take Profit  : ${self.harga_tp:,.2f}")
                else:
                    # Jika normal close (TP atau Trailing Profit), ubah status menjadi KOSONG di paling akhir proses
                    self.status_posisi = "KOSONG"
                # ======================================================================

    def on_ws_message(self, ws, message):
        try:
            data  = json.loads(message)
            kline = data['k']
            if kline['x']: self.append_candle_closed(kline)
            self.proses_trading(float(kline['c']), float(kline['v']))
        except Exception:
            pass

    def start_websocket(self):
        while True:
            self.ws_need_restart = False
            ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol_ws}@kline_{self.timeframe}"
            self.ws_app = websocket.WebSocketApp(ws_url, on_message=self.on_ws_message)
            self.ws_app.run_forever(ping_interval=30, ping_timeout=10, reconnect=0)
            time.sleep(5)

    def run(self):
        self.ambil_klines()
        Thread(
            target=self.bot_telegram.infinity_polling, 
            kwargs={"timeout": 60, "long_polling_timeout": 30}, 
            daemon=True
        ).start()
        self.start_websocket()

if __name__ == "__main__":
    bot = VPSScalperV5UpgradedV4()
    bot.run()
