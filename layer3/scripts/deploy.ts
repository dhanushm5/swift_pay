import { ethers } from "hardhat";

async function main() {
  // Get the contract factory
  const TransactionChain = await ethers.getContractFactory("TransactionChain");
  
  // Deploy the contract
  console.log("Deploying TransactionChain...");
  const transactionChain = await TransactionChain.deploy();
  
  // Wait for deployment to complete (no need for .deployed() in newer versions)
  await transactionChain.waitForDeployment();
  
  // Get the contract address
  const address = await transactionChain.getAddress();
  console.log(`TransactionChain deployed to: ${address}`);

  console.log("Deployment and setup complete!");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});