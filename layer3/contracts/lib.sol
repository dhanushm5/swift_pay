// SPDX-License-Identifier: SEE LICENSE IN LICENSE
pragma solidity ^0.8.28;

/**
 * @title TransactionLibrary
 * @dev Library containing utility functions for transaction processing
 */
library TransactionLibrary {
    /**
     * @dev Validates if a user has sufficient balance for a transaction
     * @param balances The mapping of user balances
     * @param sender The sender's UUID
     * @param amount The transaction amount
     * @return true if the sender has sufficient balance, false otherwise
     */
    function validateTransaction(
        mapping(uint256 => uint256) storage balances,
        uint256 sender, 
        uint256 amount
    ) internal view returns (bool) {
        return amount > 0 && balances[sender] >= amount;
    }

    /**
     * @dev Validates if a transaction ID already exists in the transaction list
     * @param existingTxIds Mapping to track existing transaction IDs
     * @param txid The transaction ID to check
     * @return true if the transaction ID is unique, false if it already exists
     */
    function validateTransactionId(
        mapping(uint256 => bool) storage existingTxIds,
        uint256 txid
    ) internal view returns (bool) {
        return !existingTxIds[txid];
    }

    /**
     * @dev Validates if a user exists
     * @param userExists Mapping to track existing users
     * @param uuid The user UUID to check
     * @return true if the user exists, false otherwise
     */
    function validateUser(
        mapping(uint256 => bool) storage userExists,
        uint256 uuid
    ) internal view returns (bool) {
        return userExists[uuid];
    }

    /**
     * @dev Add balance to a user's account
     * @param balances The mapping of user balances
     * @param uuid The user's UUID
     * @param amount The amount to add (must be positive)
     */
    function addBalance(
        mapping(uint256 => uint256) storage balances,
        uint256 uuid,
        uint256 amount
    ) internal {
        require(amount > 0, "Amount must be positive");
        balances[uuid] += amount;
    }

    /**
     * @dev Deduct balance from a user's account
     * @param balances The mapping of user balances
     * @param uuid The user's UUID
     * @param amount The amount to deduct (must be positive)
     * @return true if successful, false if insufficient balance
     */
    function deductBalance(
        mapping(uint256 => uint256) storage balances,
        uint256 uuid,
        uint256 amount
    ) internal returns (bool) {
        if (amount == 0 || balances[uuid] < amount) {
            return false;
        }
        unchecked {
            balances[uuid] -= amount;
        }
        return true;
    }

    /**
     * @dev Transfer balance between users
     * @param balances The mapping of user balances
     * @param sender The sender's UUID
     * @param receiver The receiver's UUID
     * @param amount The amount to transfer (must be positive)
     * @return true if successful, false if insufficient balance
     */
    function transferBalance(
        mapping(uint256 => uint256) storage balances,
        uint256 sender,
        uint256 receiver,
        uint256 amount
    ) internal returns (bool) {
        if (amount == 0 || balances[sender] < amount) {
            return false;
        }
        unchecked {
            balances[sender] -= amount;
            balances[receiver] += amount;
        }
        return true;
    }
}