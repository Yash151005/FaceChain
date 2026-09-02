"""
deploy_contract.py — Compile and Deploy FaceRecord.sol to Polygon Amoy Testnet

Run this script once to deploy the smart contract:

    python deploy_contract.py

It will:
  1. Install the Solidity 0.8.0 compiler via py-solc-x
  2. Compile contract/FaceRecord.sol
  3. Deploy to Polygon Amoy Testnet via Alchemy RPC
  4. Print the deployed contract address (paste into .env)
  5. Save the ABI to contract/FaceRecord_abi.json
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from solcx import install_solc, compile_standard
from web3 import Web3


def main():
    load_dotenv()

    rpc_url = os.getenv("ALCHEMY_RPC_URL", "")
    private_key = os.getenv("PRIVATE_KEY", "")

    if not rpc_url:
        print("ERROR: ALCHEMY_RPC_URL not set in .env")
        sys.exit(1)
    if not private_key:
        print("ERROR: PRIVATE_KEY not set in .env")
        sys.exit(1)

    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    # ── 1. Read Solidity source ──────────────────────────────────────────
    sol_path = Path(__file__).parent / "contract" / "FaceRecord.sol"
    if not sol_path.is_file():
        print(f"ERROR: Solidity file not found at {sol_path}")
        sys.exit(1)

    solidity_source = sol_path.read_text(encoding="utf-8")
    print("[1/5] Solidity source loaded.")

    # ── 2. Install compiler & compile ────────────────────────────────────
    print("[2/5] Installing Solidity compiler 0.8.0 …")
    install_solc("0.8.0")

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"FaceRecord.sol": {"content": solidity_source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "evm.bytecode"]}
                }
            },
        },
        solc_version="0.8.0",
    )

    contract_data = compiled["contracts"]["FaceRecord.sol"]["FaceRecord"]
    abi = contract_data["abi"]
    bytecode = contract_data["evm"]["bytecode"]["object"]
    print("[3/5] Contract compiled successfully.")

    # Save ABI for reference
    abi_path = Path(__file__).parent / "contract" / "FaceRecord_abi.json"
    abi_path.write_text(json.dumps(abi, indent=2), encoding="utf-8")
    print(f"       ABI saved to {abi_path}")

    # ── 3. Connect to Polygon Amoy ───────────────────────────────────────
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("ERROR: Cannot connect to RPC endpoint.")
        sys.exit(1)

    chain_id = w3.eth.chain_id
    print(f"[4/5] Connected to chain {chain_id}.", end=" ")

    if chain_id == 80002:
        print("(Polygon Amoy Testnet ✓)")
    else:
        print(f"(WARNING: Expected 80002 for Amoy, got {chain_id})")

    account = w3.eth.account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    balance_pol = w3.from_wei(balance, "ether")
    print(f"       Deployer: {account.address}")
    print(f"       Balance:  {balance_pol} POL")

    if balance == 0:
        print("ERROR: Wallet has zero balance. Get testnet POL from:")
        print("       https://faucet.polygon.technology/")
        sys.exit(1)

    # ── 4. Deploy ────────────────────────────────────────────────────────
    print("[5/5] Deploying FaceRecord contract …")

    FaceRecord = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(account.address)
    tx = FaceRecord.constructor().build_transaction({
        "chainId": chain_id,
        "from": account.address,
        "nonce": nonce,
        "gas": 1_500_000,
        "maxFeePerGas": w3.to_wei("50", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("30", "gwei"),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"       Tx sent: {tx_hash.hex()}")
    print("       Waiting for confirmation …")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt.status != 1:
        print("ERROR: Deployment transaction reverted!")
        sys.exit(1)

    contract_address = receipt.contractAddress
    print()
    print("=" * 60)
    print("  ✅  CONTRACT DEPLOYED SUCCESSFULLY")
    print("=" * 60)
    print(f"  Address:  {contract_address}")
    print(f"  Tx Hash:  {tx_hash.hex()}")
    print(f"  Block:    {receipt.blockNumber}")
    print(f"  Gas Used: {receipt.gasUsed}")
    print(f"  Explorer: https://amoy.polygonscan.com/tx/{tx_hash.hex()}")
    print()
    print("  👉  Add this to your .env file:")
    print(f"     CONTRACT_ADDRESS={contract_address}")
    print("=" * 60)


if __name__ == "__main__":
    main()
