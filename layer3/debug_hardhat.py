import os
import subprocess
import time
import socket
import json

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# Check if hardhat node is running on default port 8545
if is_port_in_use(8545):
    print("✅ Hardhat node appears to be running on port 8545")
else:
    print("❌ No service detected on port 8545. Hardhat node might not be running.")
    
    # Ask to start
    start_node = input("Do you want to start a hardhat node? (y/n): ")
    if start_node.lower() == 'y':
        print("Starting hardhat node in a new terminal...")
        
        # Use AppleScript to open a new terminal and run the command (macOS specific)
        apple_script = '''
        tell application "Terminal"
            do script "cd ~/Documents/GitHub/SwiftPay && npx hardhat node"
        end tell
        '''
        subprocess.run(["osascript", "-e", apple_script])
        
        print("Waiting for node to start...")
        time.sleep(5)  # Wait a bit for the node to initialize

# Check contract deployment
print("\nChecking if contract is deployed...")

result = subprocess.run(
    "cd ~/Documents/GitHub/SwiftPay && npx hardhat run scripts/check_deployment.js --network localhost",
    shell=True,
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print(f"Errors: {result.stderr}")

# Create check_deployment.js if it doesn't exist
if not os.path.exists("~/Documents/GitHub/SwiftPay/scripts/check_deployment.js"):
    os.makedirs("~/Documents/GitHub/SwiftPay/scripts", exist_ok=True)
    with open("~/Documents/GitHub/SwiftPay/scripts/check_deployment.js", "w") as f:
        f.write('''
const { ethers } = require("hardhat");

async function main() {
  try {
    const provider = ethers.provider;
    const network = await provider.getNetwork();
    console.log(`Connected to network: ${network.name} (chainId: ${network.chainId})`);
    
    const accounts = await ethers.getSigners();
    console.log(`Found ${accounts.length} accounts. First account: ${accounts[0].address}`);
    
    const balance = await provider.getBalance(accounts[0].address);
    console.log(`Account balance: ${ethers.formatEther(balance)} ETH`);
    
    // Try to connect to the contract at the address from .env
    require('dotenv').config();
    const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;
    
    if (!CONTRACT_ADDRESS) {
      console.log("No contract address found in .env file");
      return;
    }
    
    console.log(`Checking contract at address: ${CONTRACT_ADDRESS}`);
    
    // Get code at address to see if contract exists
    const code = await provider.getCode(CONTRACT_ADDRESS);
    if (code === '0x') {
      console.log("⚠️ No contract found at this address!");
      
      // Ask about deploying
      console.log("Do you want to deploy a new contract? Run:");
      console.log("npx hardhat run scripts/deploy.js --network localhost");
    } else {
      console.log("✅ Contract found at address!");
      
      // Try to connect to it
      const TransactionChain = await ethers.getContractFactory("TransactionChain");
      const contract = TransactionChain.attach(CONTRACT_ADDRESS);
      
      try {
        const txCount = await contract.getTransactionCount();
        console.log(`Contract connected successfully. Transaction count: ${txCount}`);
      } catch (error) {
        console.log(`Error connecting to contract: ${error.message}`);
      }
    }
  } catch (error) {
    console.error(`Error: ${error.message}`);
  }
}

main().catch(console.error);
        ''')

print("\nTroubleshooting steps if your contract isn't connecting:")
print("1. Make sure Hardhat node is running in a separate terminal:")
print("   npx hardhat node")
print("2. Deploy your contract (if not already deployed):")
print("   npx hardhat run scripts/deploy.js --network localhost")
print("3. Update the CONTRACT_ADDRESS in your .env file with the output address")
print("4. Restart your FastAPI server")