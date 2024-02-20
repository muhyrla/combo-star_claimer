import asyncio
import aiohttp
from web3 import Web3
import requests
from web3.middleware import geth_poa_middleware
from time import sleep

combo_url = 'https://rpc.combonetwork.io'
w3_combo = Web3(Web3.HTTPProvider(combo_url))

MAX_CONCURRENT_TASKS = 5 # ТУТ КОЛ-ВО ОДНОВРЕМЕННЫХ ПОТОКОВ
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

async def get_dummy_signature(address):
    strict_data = {
        "nft_contract":"0x20Cb10B8f601d4B2C62962BB938554F3824e24f3",
        "mint_contract":"0x514A16EDd7A916efC662d1E360684602fd72DCD7",
        "mint_to":address,
        "chain_id":9980
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://combonetwork.io/api/mint/sign', json=strict_data) as response:
            data = await response.json()
            return data['data']['dummy_id'], data['data']['signature']


async def join_social(address):
    strict_data = {
        "address":address,
        "chain_id":9980
    }
    try:
        async with aiohttp.ClientSession() as session:
            tasks = [
                session.post('https://combonetwork.io/api/discord/join', json=strict_data),
                session.post('https://combonetwork.io/api/twitter/bind', json=strict_data),
                session.post('https://combonetwork.io/api/telegram/join', json=strict_data)
            ]
            responses = await asyncio.gather(*tasks)
            for response in responses:
                print(await response.json())
            return True
    except:
        return False


async def bridge_bnb(private_key):
    w3_bnb = Web3(Web3.HTTPProvider('https://rpc.ankr.com/bsc'))
    contract_address = '0xAF0721ecf5B087eF67731188925C83DBC02f46Fb'

    to_bridge = '0.00002'
    mingaslimit = 1
    extrabytes = b'64'

    account = w3_bnb.eth.account.from_key(private_key)

    with open('ABI_bridge.txt', 'r') as abi_file:
        abi = abi_file.read()
        contract = w3_bnb.eth.contract(address=contract_address, abi=abi)
        w3_bnb.middleware_onion.inject(geth_poa_middleware, layer=0)

        transaction_est = contract.functions.bridgeETH(mingaslimit, extrabytes).build_transaction({
            'from': account.address,
            'value': w3_bnb.to_wei(to_bridge, 'ether'),
            'nonce': w3_bnb.eth.get_transaction_count(account.address),
            'maxPriorityFeePerGas': w3_bnb.to_wei('1', 'gwei'),
            'maxFeePerGas': w3_bnb.to_wei('3', 'gwei')
        })

        gas_estimate = w3_bnb.eth.estimate_gas(transaction_est)

        transaction = contract.functions.bridgeETH(mingaslimit, extrabytes).build_transaction({
            'value': w3_bnb.to_wei(to_bridge, 'ether'),
            'gas': gas_estimate,
            'from': account.address,
            'nonce': w3_bnb.eth.get_transaction_count(account.address),
            'maxPriorityFeePerGas': w3_bnb.to_wei('1', 'gwei'),
            'maxFeePerGas': w3_bnb.to_wei('3', 'gwei')
        })

        signed_tx = w3_bnb.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3_bnb.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f'Успешно забриджил {tx_hash.hex()}')
        await asyncio.sleep(100)
        return True


async def mint_nft(private_key):
    combo_url = 'https://rpc.combonetwork.io'
    w3_combo = Web3(Web3.HTTPProvider(combo_url))
    contract_address = Web3.to_checksum_address('0x514a16edd7a916efc662d1e360684602fd72dcd7')
    account = w3_combo.eth.account.from_key(private_key)

    dummy, sign = await get_dummy_signature(account.address)
    nft = Web3.to_checksum_address('0x20cb10b8f601d4b2c62962bb938554f3824e24f3')
    mint_to = account.address

    with open('ABI_mint.txt', 'r') as abi_file:
        contract = w3_combo.eth.contract(address=contract_address, abi=abi_file.read())
        w3_combo.middleware_onion.inject(geth_poa_middleware, layer=0)

        signb = sign.encode()

        transaction = contract.functions.claim(nft, int(dummy), mint_to, str(sign)).build_transaction({
            'value': w3_combo.to_wei(0, 'ether'),
            'gas': 330000,
            'gasPrice': w3_combo.eth.gas_price,
            'from': account.address,
            'nonce': w3_combo.eth.get_transaction_count(account.address)
        })

        signed_tx = w3_combo.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3_combo.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f'Заминтил {tx_hash.hex()}')
        return True


async def process_account(private_key):
    async with semaphore:
        account = w3_combo.eth.account.from_key(private_key)
        print(f'Working with {account.address}')
        try:
            if await bridge_bnb(private_key):
                if await join_social(account.address):
                    try:
                        await mint_nft(private_key)
                    except Exception as e:
                        print(f"Error minting NFT: {e}")
                        with open('after_bridge.txt', 'a') as f:
                            f.write(private_key + '\n')
                        return
        except Exception as e:
            print(f"Error bridging BNB: {e}")
            with open('before_bridge.txt', 'a') as f:
                f.write(private_key + '\n')
            return


async def main():
    with open('accounts.txt', 'r') as acc_files:
        prv_keys = acc_files.readlines()
        tasks = [process_account(key.replace('\n', '').split(';')[0]) for key in prv_keys]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
