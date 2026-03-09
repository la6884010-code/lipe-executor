import os
import ccxt
import time
import win32com.client as wincl
import winsound
import requests
import random
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# --- [ CORES ANSI ] ---
RESET   = "\033[0m"
VERDE   = "\033[92m"
AMARELO = "\033[93m"
CIANO   = "\033[96m"
VERMELHO= "\033[91m"
ROXO    = "\033[95m"
NEGRITO = "\033[1m"
AZUL    = "\033[94m"
BRANCO  = "\033[97m"
CINZA   = "\033[90m"
LARANJA = "\033[38;5;214m"
NEON    = "\033[95m"
SPARK   = "\033[97m"

# --- [ DADOS DE CONEXÃO ] ---
CHAVE_BINANCE    = os.getenv('CHAVE_BINANCE')
SECRET_BINANCE   = os.getenv('SECRET_BINANCE')
CHAVE_NOVADAX    = os.getenv('CHAVE_NOVADAX')
SECRET_NOVADAX   = os.getenv('SECRET_NOVADAX')
TOKEN_TELEGRAM   = os.getenv('TOKEN_TELEGRAM')
CHAT_ID_TELEGRAM = os.getenv('CHAT_ID_TELEGRAM')

# --- [ CONFIGURACAO DA VOZ ] ---
# Volume: 0 a 100 | Velocidade: -10 (lenta) a 10 (rapida), 0 = normal
VOLUME_VOZ     = 100
VELOCIDADE_VOZ = 5

def falar(texto):
    try:
        voz = wincl.Dispatch("SAPI.SpVoice")
        voz.Volume = VOLUME_VOZ
        voz.Rate   = VELOCIDADE_VOZ
        voz.Speak(texto)
    except: pass

def enviar_telegram(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage?chat_id={CHAT_ID_TELEGRAM}&text={msg}", timeout=5)
    except: pass

binance = ccxt.binance({
    'apiKey': CHAVE_BINANCE,
    'secret': SECRET_BINANCE,
    'enableRateLimit': True,
    'options': {
        'adjustForTimeDifference': True
    }
})

novadax = ccxt.novadax({
    'apiKey': CHAVE_NOVADAX,
    'secret': SECRET_NOVADAX,
    'enableRateLimit': True
})

def buscar_ticker_binance(par):
    return ('binance', binance.fetch_ticker(par))

def buscar_ticker_novadax(par):
    return ('novadax', novadax.fetch_ticker(par))

def imprimir_painel(maior_margem, maior_rota, maior_hora, margem_atual, rota_atual, hora_atual, oportunidades):
    cor_rec   = VERDE if maior_margem > 0 else VERMELHO
    cor_atu   = VERDE if margem_atual > 0.1 else VERMELHO
    icone_rec = "📗" if maior_rota == "DIRETA" else "📙"
    icone_atu = "📗" if rota_atual == "DIRETA" else "📙"
    borda = "══════════════════════════════════════════════"
    print(f"\n{NEON}{NEGRITO}╔{borda}╗{RESET}")
    print(f"{NEON}{NEGRITO}║  {AMARELO}🏆  MAIOR MARGEM VISTA HOJE{NEON}                 ║{RESET}")
    print(f"{NEON}{NEGRITO}╠{borda}╣{RESET}")
    if maior_rota == "---":
        print(f"{NEON}{NEGRITO}║  {AMARELO}Nenhuma margem positiva ainda hoje{NEON}          ║{RESET}")
        print(f"{NEON}{NEGRITO}║  {CINZA}Aguardando oportunidade...{NEON}                   ║{RESET}")
    else:
        status = f"{VERDE}✅ Gerou operação{NEON}         " if maior_margem >= 0.6 else f"{AMARELO}⏳ Abaixo do gatilho (0.60%){NEON}"
        print(f"{NEON}{NEGRITO}║  {CINZA}Recorde:{RESET} {cor_rec}{NEGRITO}{maior_margem:>6.2f}%{RESET} {icone_rec} {CIANO}{maior_rota:<7}{RESET} {LARANJA}{maior_hora}{NEON} ║{RESET}")
        print(f"{NEON}{NEGRITO}║  {CINZA}Status :{RESET} {status}║{RESET}")
    print(f"{NEON}{NEGRITO}║  {CINZA}Atual  :{RESET} {cor_atu}{NEGRITO}{margem_atual:>6.2f}%{RESET} {icone_atu} {CIANO}{rota_atual:<7}{RESET} {LARANJA}{hora_atual}{NEON} ║{RESET}")
    print(f"{NEON}{NEGRITO}║  {CINZA}Oport. :{RESET} {VERDE}{oportunidades}x positivas hoje{NEON}              ║{RESET}")
    print(f"{NEON}{NEGRITO}╚{borda}╝{RESET}\n")

def executar_arbitragem():
    print(f"{VERDE}{NEGRITO}{'='*75}{RESET}")
    print(f"{VERDE}{NEGRITO} >>> LUK2 — INTELIGÊNCIA ARTIFICIAL PROCURANDO LUCRO <<< {RESET}")
    print(f"{VERDE}{NEGRITO}{'='*75}{RESET}")
    falar("LUK2. Inteligência artificial procurando lucro.")

    # --- Mensagem de ativação no Telegram ---
    enviar_telegram(
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  SISTEMA ALFA — ATIVADO\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Status  : Online\n"
        f"  Inicio  : {time.strftime('%H:%M:%S')}\n"
        f"  Missao  : Monitorar mercado 24h\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Inteligencia Artificial em operacao"
    )

    contador_linhas = 0
    internet_ativa = True
    par = 'USDT/BRL'
    snapshot_precos = ""

    # --- Historico para relatorio de queda ---
    hora_queda     = "--:--:--"
    snapshot_queda = "Sem dados anteriores" 

    # --- Recordes do dia ---
    maior_margem = 0.0
    maior_rota   = "---"
    maior_hora   = "--:--:--"
    oportunidades_positivas = 0
    contador_total = 0
    historico_linhas = []

    # --- Controle do relatório de 10 em 10 minutos ---
    ultimo_relatorio = time.time()

    while True:
        try:
            # --- BUSCA EM PARALELO ---
            resultados = {}
            with ThreadPoolExecutor(max_workers=2) as executor:
                futuros = {
                    executor.submit(buscar_ticker_binance, par): 'binance',
                    executor.submit(buscar_ticker_novadax, par): 'novadax'
                }
                for futuro in as_completed(futuros):
                    nome, ticker = futuro.result()
                    resultados[nome] = ticker

            tk_b = resultados['binance']
            tk_n = resultados['novadax']

            pb_ask, pn_bid = tk_b['ask'], tk_n['bid']
            m_direta  = (((pn_bid - pb_ask) / pb_ask) - 0.003) * 100
            m_inversa = (((tk_b['bid'] - tk_n['ask']) / tk_n['ask']) - 0.003) * 100

            saldo = novadax.fetch_balance()['total'].get('USDT', 0)
            ts    = time.strftime('%H:%M:%S')

            snapshot_precos = f"Bina: R$ {pb_ask:.2f} | Nova: R$ {pn_bid:.2f} | Saldo: {saldo:.2f} USDT"

            margem_final = max(m_direta, m_inversa)
            rota = "DIRETA" if m_direta > m_inversa else "INVERSA"
            if margem_final > 0:
                oportunidades_positivas += 1

            # --- Atualiza recorde do dia ---
            if margem_final > maior_margem:
                maior_margem = margem_final
                maior_rota   = rota
                maior_hora   = ts

            if contador_linhas >= 10:
                imprimir_painel(maior_margem, maior_rota, maior_hora, margem_final, rota, ts, oportunidades_positivas)
                falar("Inteligência Artificial monitorando ao vivo mercado financeiro")
                contador_linhas = 0

            cor_margem = VERDE if margem_final > 0.1 else VERMELHO
            cor_rota   = VERDE if rota == "DIRETA" else LARANJA
            icone_rota = "📗" if rota == "DIRETA" else "📙"
            linha = (
                f"{CINZA}[{ts}]{RESET} │ "
                f"{CIANO}🔎 USDT/BRL{RESET} │ "
                f"{CINZA}BINA:{RESET} {AZUL}R$ {pb_ask:.2f}{RESET} │ "
                f"{CINZA}NOVA:{RESET} {ROXO}R$ {pn_bid:.2f}{RESET} │ "
                f"{CINZA}Margem:{RESET} {cor_margem}{NEGRITO}{margem_final:.2f}%{RESET} "
                f"{cor_rota}{icone_rota} {rota}{RESET} │ "
                f"💰 {AMARELO}{saldo:.2f} USDT{RESET} │ "
                f"🏆 {VERDE}{maior_margem:.2f}%{RESET}"
            )
            print(linha)
            historico_linhas.append(linha)
            if len(historico_linhas) > 10:
                historico_linhas.pop(0)
            contador_linhas += 1
            contador_total  += 1
            if contador_total >= 20:
                print(f"\n{CINZA}── 🔄 Atualizando...{RESET}")
                for _ in range(20):
                    print()
                    time.sleep(0.05)
                os.system('cls')
                for l in historico_linhas:
                    print(l)
                contador_total = 0

            # --- Salva snapshot atual para historico de queda ---
            snapshot_queda = snapshot_precos

            if not internet_ativa:
                hora_reconexao = time.strftime('%H:%M:%S')
                enviar_telegram(
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🟢 SISTEMA ALFA — RECONECTADO\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Status     : Online\n"
                    f"  Queda em   : {hora_queda}\n"
                    f"  Retorno em : {hora_reconexao}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Ultimo snapshot antes da queda:\n"
                    f"  {snapshot_queda}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Monitoramento retomado automaticamente"
                )
                internet_ativa = True

            # --- Relatório de 10 em 10 minutos ---
            agora = time.time()
            if agora - ultimo_relatorio >= 600:
                enviar_telegram(
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  RELATORIO DE ESTADO — {ts}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Status   : Operando normalmente\n"
                    f"  Binance  : R$ {pb_ask:.2f}\n"
                    f"  NovaDax  : R$ {pn_bid:.2f}\n"
                    f"  Saldo    : {saldo:.2f} USDT\n"
                    f"  Margem   : {margem_final:.2f}% ({rota})\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Recorde do dia\n"
                    f"  Margem   : {maior_margem:.2f}% ({maior_rota})\n"
                    f"  Horario  : {maior_hora}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Proximo relatorio em 10 minutos"
                )
                ultimo_relatorio = agora

            if margem_final > 0.6:
                winsound.Beep(2000, 1000)
                if rota == "DIRETA":
                    binance.create_market_buy_order(par, 195)
                    time.sleep(1)
                    novadax.create_market_sell_order(par, novadax.fetch_balance()['total'].get('USDT', 0))
                else:
                    novadax.create_market_buy_order(par, 195)
                    time.sleep(1)
                    binance.create_market_sell_order(par, binance.fetch_balance()['total'].get('USDT', 0))
                enviar_telegram(
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  OPERACAO EXECUTADA\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Lucro    : +{margem_final:.2f}%\n"
                    f"  Rota     : {rota}\n"
                    f"  Horario  : {ts}\n"
                    f"  Binance  : R$ {pb_ask:.2f}\n"
                    f"  NovaDax  : R$ {pn_bid:.2f}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Saldo    : {saldo:.2f} USDT"
                )

            time.sleep(random.uniform(2, 5))

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            if internet_ativa:
                hora_queda = time.strftime('%H:%M:%S')
                print(f"{VERMELHO}🚨 OSCILAÇÃO DETECTADA! Enviando perícia técnica...{RESET}")
                falar("Erro detectado. Verifique seu telegram.")
                relatorio = (
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 ALERTA — QUEDA DETECTADA\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Horario  : {hora_queda}\n"
                    f"  Erro     : {str(e)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"  Ultimo snapshot:\n"
                    f"  {snapshot_queda}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🟡 Reconectando automaticamente..."
                )
                enviar_telegram(relatorio)
                internet_ativa = False

            time.sleep(10)
            gc.collect()

if __name__ == "__main__":
    executar_arbitragem()
