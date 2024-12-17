import aiohttp
import asyncio
import aiofiles
import aioconsole
import json
import os
import random
import string
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置默认请求头
headers = {
    'Content-Type': 'application/json',
}

# coday 函数
async def coday(url, method, headers, payload_data=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=payload_data) as response:
                try:
                    json_data = await response.json()
                except aiohttp.ContentTypeError:
                    json_data = {}
                if not response.ok:
                    return {'error': True, 'status': response.status, 'data': json_data}
                return json_data
    except Exception as e:
        logger.error(f"Error in coday: {e}")
        return {'error': True, 'message': str(e)}

# 注册函数
async def register(session, name, email, password, referral_code):
    payload_reg = {
        "full_name": name,
        "email": email,
        "password": password,
        "referral_code": referral_code,
    }
    return await coday('https://api.meshchain.ai/meshmain/auth/email-signup', 'POST', headers, payload_reg)

# 登录函数
async def login(session, email, password):
    payload_login = {
        "email": email,
        "password": password,
    }
    return await coday('https://api.meshchain.ai/meshmain/auth/email-signin', 'POST', headers, payload_login)

# 验证邮箱函数
async def verify(session, email, otp):
    payload_verify = {
        "email": email,
        "code": otp,
    }
    return await coday('https://api.meshchain.ai/meshmain/auth/verify-email', 'POST', headers, payload_verify)

# 领取奖励函数
async def claim_bnb(session):
    payload_claim = {"mission_id": "ACCOUNT_VERIFICATION"}
    return await coday('https://api.meshchain.ai/meshmain/mission/claim', 'POST', headers, payload_claim)

# 生成 16 字节的十六进制字符串
def generate_hex():
    return ''.join(random.choices(string.hexdigits, k=16))

# 初始化节点并保存唯一 ID
async def init(session, random_hex):
    url = "https://api.meshchain.ai/meshmain/nodes/link"
    payload = {
        "unique_id": random_hex,
        "node_type": "browser",
        "name": "Extension"
    }
    return await coday(url, 'POST', headers, payload)

# estimate 函数
async def estimate(session, id, headers):
    url = 'https://api.meshchain.ai/meshmain/rewards/estimate'
    return await coday(url, 'POST', headers, {'unique_id': id})

# claim 函数
async def claim(session, id, headers):
    url = 'https://api.meshchain.ai/meshmain/rewards/claim'
    result = await coday(url, 'POST', headers, {'unique_id': id})
    return result.get('total_reward', None)

# start 函数
async def start(session, id, headers):
    url = 'https://api.meshchain.ai/meshmain/rewards/start'
    return await coday(url, 'POST', headers, {'unique_id': id})

# info 函数
async def info(session, id, headers):
    url = 'https://api.meshchain.ai/meshmain/nodes/status'
    return await coday(url, 'POST', headers, {'unique_id': id})

# 主函数
async def main():
    async with aiohttp.ClientSession() as session:
        try:
            # 提示用户输入需要注册的账号数量
            num_accounts = int(await aioconsole.ainput("请输入需要注册的账号数量: "))

            for _ in range(num_accounts):
                # 提示用户依次输入信息
                name = await aioconsole.ainput("请输入您的姓名: ")
                email = await aioconsole.ainput("请输入您的邮箱: ")
                password = await aioconsole.ainput("请输入您的密码: ")
                referral_code = await aioconsole.ainput("请输入邀请码 (默认: UXFQ1RX2KTZA): ") or "UXFQ1RX2KTZA"

                # 注册账户
                register_message = await register(session, name, email, password, referral_code)
                logger.info(f"注册结果: {register_message}")

                # 登录账户
                login_data = await login(session, email, password)
                if not login_data:
                    continue

                # 将 access token 添加到请求头
                global headers
                headers['Authorization'] = f"Bearer {login_data['access_token']}"

                # 验证邮箱
                otp = await aioconsole.ainput("请输入您收到的邮箱验证码 (OTP): ")
                verify_message = await verify(session, email, otp)
                logger.info(f"邮箱验证结果: {verify_message}")

                # 领取奖励
                claim_message = await claim_bnb(session)
                logger.info(f"奖励领取成功: {claim_message}")

                # 生成并链接唯一 ID
                random_hex = generate_hex()
                link_response = await init(session, random_hex)

                # 保存令牌和唯一 ID
                try:
                    async with aiofiles.open('token.txt', 'a') as token_file:
                        await token_file.write(f"{login_data['access_token']}|{login_data['refresh_token']}\n")
                    logger.info('令牌已保存到 token.txt')

                    async with aiofiles.open('unique_id.txt', 'a') as id_file:
                        await id_file.write(f"{link_response['unique_id']}\n")
                    logger.info('扩展 ID 已保存到 unique_id.txt')

                    # 启动节点
                    starting = await start(session, link_response['unique_id'], headers)
                    if starting:
                        logger.info(f"扩展 ID: {link_response['unique_id']} 已激活")
                except Exception as e:
                    logger.error('保存数据到文件失败:', e)
        except Exception as e:
            logger.error("程序运行时发生错误:", e)

# 启动程序
if __name__ == "__main__":
    asyncio.run(main())
