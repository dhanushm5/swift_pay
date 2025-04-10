
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
        