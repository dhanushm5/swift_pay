import {
  time,
  loadFixture,
} from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { anyValue } from "@nomicfoundation/hardhat-chai-matchers/withArgs";
import { expect } from "chai";
import { ethers } from "hardhat";

describe("TransactionChain", function () {

  async function deployTransactionChainFixture() {
    // singers
    const [owner, addr1, addr2] = await ethers.getSigners();

    // Deploy the TransactionChain contract
    const TransactionChain = await ethers.getContractFactory("TransactionChain");
    const transactionChain = await TransactionChain.deploy();

    return { transactionChain, owner, addr1, addr2 };
  }

  describe("User Management", function () {
    it("Should create a new user successfully", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      // User UUID
      const uuid = 12345;
      
      // Create user
      await expect(transactionChain.createUser(uuid))
        .to.emit(transactionChain, "UserCreated")
        .withArgs(uuid, anyValue);
      
      // Verify user exists
      expect(await transactionChain.validateUser(uuid)).to.equal(true);
    });

    it("Should not create duplicate users", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      const uuid = 12345;
      
      // Create user
      await transactionChain.createUser(uuid);
      
      //Check dupes
      const result = await transactionChain.createUser.staticCall(uuid);
      expect(result).to.equal(false);
      
      // Check user creation evetn
      await expect(transactionChain.createUser(uuid))
        .to.not.emit(transactionChain, "UserCreated");
    });

    it("Should add balance to a user", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      const uuid = 12345;
      const amount = ethers.parseEther("1.0");
      
      await transactionChain.createUser(uuid);
      
      await expect(transactionChain.userAdd(uuid, amount))
        .to.emit(transactionChain, "BalanceAdded")
        .withArgs(uuid, amount, amount);
      
      expect(await transactionChain.balances(uuid)).to.equal(amount);
    });

    it("Should deposit ETH to user balance", async function () {
      const { transactionChain, owner } = await loadFixture(deployTransactionChainFixture);
      
      const uuid = 12345;
      const depositAmount = ethers.parseEther("0.5");
      
      await transactionChain.createUser(uuid);
      
      await expect(transactionChain.deposit(uuid, { value: depositAmount }))
        .to.emit(transactionChain, "BalanceAdded")
        .withArgs(uuid, depositAmount, depositAmount);
      
      // Verify balance
      expect(await transactionChain.balances(uuid)).to.equal(depositAmount);
    });
  });

  describe("Transaction Processing", function () {
    it("Should create a transaction between users", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      const sender = 12345;
      const receiver = 67890;
      const amount = ethers.parseEther("0.5");
      const txid = 1;
      
      await transactionChain.createUser(sender);
      await transactionChain.createUser(receiver);
      
      await transactionChain.userAdd(sender, ethers.parseEther("1.0"));
      
      await expect(transactionChain.createTransaction(sender, receiver, amount, txid))
        .to.emit(transactionChain, "TransactionCreated")
        .withArgs(sender, receiver, amount, anyValue, txid);
      
      expect(await transactionChain.balances(sender)).to.equal(ethers.parseEther("0.5"));
      expect(await transactionChain.balances(receiver)).to.equal(amount);
    });

    it("Should fail when sender has insufficient balance", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      const sender = 12345;
      const receiver = 67890;
      const amount = ethers.parseEther("1.0");
      const txid = 1;
      
      await transactionChain.createUser(sender);
      await transactionChain.createUser(receiver);
      
      await transactionChain.userAdd(sender, ethers.parseEther("0.5"));
      
      await expect(transactionChain.createTransaction(sender, receiver, amount, txid))
        .to.be.revertedWith("Insufficient balance");
    });

    it("Should not allow duplicate transaction IDs", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      const sender = 12345;
      const receiver = 67890;
      const amount = ethers.parseEther("0.2");
      const txid = 1;
      
      await transactionChain.createUser(sender);
      await transactionChain.createUser(receiver);
      
      await transactionChain.userAdd(sender, ethers.parseEther("1.0"));
      
      await transactionChain.createTransaction(sender, receiver, amount, txid);
      
      await expect(transactionChain.createTransaction(sender, receiver, amount, txid))
        .to.be.revertedWith("Transaction ID already exists");
    });
  });

  describe("Transaction Retrieval", function () {
    it("Should retrieve transaction details by ID", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      const sender = 12345;
      const receiver = 67890;
      const amount = ethers.parseEther("0.3");
      const txid = 1;
      
      await transactionChain.createUser(sender);
      await transactionChain.createUser(receiver);
      await transactionChain.userAdd(sender, ethers.parseEther("1.0"));
      await transactionChain.createTransaction(sender, receiver, amount, txid);
      
      const [found, txSender, txReceiver, txAmount, timestamp] = await transactionChain.getTransaction(txid);
      
      expect(found).to.equal(true);
      expect(txSender).to.equal(sender);
      expect(txReceiver).to.equal(receiver);
      expect(txAmount).to.equal(amount);
      expect(timestamp).to.be.gt(0);
    });

    it("Should return user transaction history", async function () {
      const { transactionChain } = await loadFixture(deployTransactionChainFixture);
      
      const sender = 12345;
      const receiver = 67890;
      const amount1 = ethers.parseEther("0.1");
      const amount2 = ethers.parseEther("0.2");
      const txid1 = 1;
      const txid2 = 2;
      
      await transactionChain.createUser(sender);
      await transactionChain.createUser(receiver);
      await transactionChain.userAdd(sender, ethers.parseEther("1.0"));
      
      await transactionChain.createTransaction(sender, receiver, amount1, txid1);
      await transactionChain.createTransaction(sender, receiver, amount2, txid2);
      
      const [txIds, senders, receivers, amounts] = await transactionChain.getUserTransactions(sender);
      
      expect(txIds.length).to.equal(2);
      expect(senders[0]).to.equal(sender);
      expect(receivers[0]).to.equal(receiver);
      expect(amounts[0]).to.equal(amount1);
      expect(txIds[1]).to.equal(txid2);
    });
  });
});