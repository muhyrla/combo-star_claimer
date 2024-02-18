from web3 import Web3
import requests
from web3.middleware import geth_poa_middleware
from time import sleep

combo_url = 'https://rpc.combonetwork.io'
w3_combo = Web3(Web3.HTTPProvider(combo_url))


def get_dummy_signature(address):
    strict_data = {
        "nft_contract":"0x20Cb10B8f601d4B2C62962BB938554F3824e24f3",
        "mint_contract":"0x514A16EDd7A916efC662d1E360684602fd72DCD7",
        "mint_to":address,
        "chain_id":9980
    }
    sign_data = requests.post('https://combonetwork.io/api/mint/sign', json=strict_data)
    return sign_data.json()['data']['dummy_id'], sign_data.json()['data']['signature']


def join_social(address):
    strict_data = {
        "address":address,
        "chain_id":9980
    }
    try:
        discord = requests.post('https://combonetwork.io/api/discord/join', json=strict_data)
        twitter = requests.post('https://combonetwork.io/api/twitter/bind', json=strict_data)
        telegram = requests.post('https://combonetwork.io/api/telegram/join', json=strict_data)
        print(discord.json(), twitter.json(), telegram.json())
        return True
    except:
        return False


def bridge_bnb(private_key):
    w3_bnb = Web3(Web3.HTTPProvider('https://rpc.ankr.com/bsc'))
    contract_address = '0xAF0721ecf5B087eF67731188925C83DBC02f46Fb'

    to_bridge = '0.001'
    mingaslimit = 1
    extrabytes = b'64'

    account = w3_bnb.eth.account.from_key(private_key)

    with(open('ABI_bridge.txt', 'r')) as abi_file:
        abi = abi_file.read()
        contract = w3_bnb.eth.contract(address=contract_address, abi=abi)
        w3_bnb.middleware_onion.inject(geth_poa_middleware, layer=0)

        transaction = contract.functions.bridgeETH(mingaslimit, extrabytes).build_transaction({
        'value': w3_bnb.to_wei(to_bridge, 'ether'),
        'gas': 250000,
        'gasPrice': w3_bnb.eth.gas_price,
        'from': account.address,
        'nonce': w3_bnb.eth.get_transaction_count(account.address)
        }) 

        signed_tx = w3_bnb.eth.account.sign_transaction(transaction, private_key)
        tx_hash = w3_bnb.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f'Успешно забриджил {tx_hash.hex()}')
        sleep(100)
        return True


def mint_nft(private_key):
    combo_url = 'https://rpc.combonetwork.io'
    w3_combo = Web3(Web3.HTTPProvider(combo_url))
    contract_address = Web3.to_checksum_address('0x514a16edd7a916efc662d1e360684602fd72dcd7')
    account = w3_combo.eth.account.from_key(private_key)

    dummy, sign = get_dummy_signature(account.address)
    nft = Web3.to_checksum_address('0x20cb10b8f601d4b2c62962bb938554f3824e24f3')
    mint_to = account.address

    with(open('ABI_mint.txt', 'r')) as abi_file:
        contract = w3_combo.eth.contract(address=contract_address, abi=abi_file.read())
        w3_combo.middleware_onion.inject(geth_poa_middleware, layer=0)

        signb = sign.encode()

        # address,uint256,address,bytes
        # str,    str,    address,str
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


if __name__ == "__main__":
    with(open('accounts.txt', 'r')) as acc_files:
        prv_keys = acc_files.readlines()
        for key in prv_keys:
            prv_key = key.replace('\n')
            account = w3_combo.eth.account.from_key(prv_key)
            
            if bridge_bnb(prv_key):
                if join_social(account.address):
                    mint_nft(prv_key)