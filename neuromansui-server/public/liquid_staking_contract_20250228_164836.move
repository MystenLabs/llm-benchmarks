// This is a complete Sui Move smart contract implementing a simple liquid staking protocol.
// The module is named "my_module" and is deployed under the address 0x0 (temp_addr).
// It provides functions for initializing a staking pool, staking SUI tokens to obtain a liquid ticket,
// unstaking (with an optional lock period), delegation to validators, and rewards distribution.

address 0x0 {

module my_module {

    // Import standard vector library.
    use std::vector;
    // Import the transaction context to retrieve the caller's address.
    use sui::tx_context::TxContext;

    // Struct representing the delegation of staked SUI to a validator.
    // Each delegation record stores the validator's address and the amount delegated.
    struct Delegation has store {
        validator: address,
        amount: u64,
    }

    // Struct representing the staking pool.
    // Fields:
    // - admin: the owner/administrator of this pool. Only the admin can perform privileged actions.
    // - total_staked: the total amount of SUI staked in the pool.
    // - total_rewards: the total rewards accrued in the pool.
    // - ticket_counter: a counter used to assign unique identifiers for each liquid ticket.
    // - delegations: a vector storing delegation information to validators.
    struct StakingPool has key, store {
        admin: address,
        total_staked: u64,
        total_rewards: u64,
        ticket_counter: u64,
        delegations: vector<Delegation>,
    }

    // Struct representing a liquid staking ticket issued to users when they stake SUI.
    // Fields:
    // - id: a unique identifier for the ticket.
    // - owner: the address of the ticket owner.
    // - amount: the amount of SUI staked represented by this ticket.
    // - lock_until: the timestamp until which unstaking is locked.
    struct LiquidTicket has store {
        id: u64,
        owner: address,
        amount: u64,
        lock_until: u64,
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////////
    // Function: init_pool
    //
    // Initializes a new staking pool.
    // The pool's admin is set to the caller of this function.
    //
    // Parameters:
    // - ctx: Transaction context used to retrieve the caller's address.
    //
    // Returns:
    // - A new instance of StakingPool with initial values.
    ////////////////////////////////////////////////////////////////////////////////////////////////////
    public fun init_pool(ctx: &mut TxContext): StakingPool {
        let admin = TxContext::sender(ctx);
        StakingPool {
            admin,
            total_staked: 0,
            total_rewards: 0,
            ticket_counter: 0,
            delegations: vector::empty<Delegation>(),
        }
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////////
    // Function: stake
    //
    // Stakes a specified amount of SUI, increasing the pool's total staked value and issuing a liquid ticket.
    // The liquid ticket represents the staked amount and includes a lock period during which unstaking is disabled.
    //
    // Parameters:
    // - ctx: Transaction context used to retrieve the caller's address.
    // - pool: A mutable reference to the staking pool.
    // - amount: The amount of SUI to stake.
    // - lock_duration: The duration (in the same time unit as 'now') for which staking is locked.
    // - now: The current timestamp.
    //
    // Returns:
    // - A LiquidTicket representing the user's staked position.
    ////////////////////////////////////////////////////////////////////////////////////////////////////
    public fun stake(
        ctx: &mut TxContext,
        pool: &mut StakingPool,
        amount: u64,
        lock_duration: u64,
        now: u64
    ): LiquidTicket {
        let user = TxContext::sender(ctx);
        // Increase the total staked amount in the pool.
        pool.total_staked = pool.total_staked + amount;
        // Generate a unique ticket id and update the counter.
        let ticket_id = pool.ticket_counter;
        pool.ticket_counter = pool.ticket_counter + 1;
        // Calculate the lock expiration time.
        let lock_until = now + lock_duration;
        // Issue a liquid ticket to the user.
        LiquidTicket {
            id: ticket_id,
            owner: user,
            amount,
            lock_until,
        }
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////////
    // Function: unstake
    //
    // Unstakes a specified amount of SUI from a liquid ticket.
    // Validates that the caller is the owner of the ticket, the lock period has passed,
    // and that the unstake amount does not exceed the ticket's staked amount.
    // The pool's total staked value is reduced accordingly.
    //
    // Parameters:
    // - ctx: Transaction context used to retrieve the caller's address.
    // - pool: A mutable reference to the staking pool.
    // - ticket: The liquid ticket being used to unstake.
    // - unstake_amount: The amount of SUI the user wants to unstake.
    // - now: The current timestamp.
    //
    // Returns:
    // - A LiquidTicket with the updated staked amount. If the entire amount is unstaked,
    //   the ticket's amount will be 0.
    ////////////////////////////////////////////////////////////////////////////////////////////////////
    public fun unstake(
        ctx: &mut TxContext,
        pool: &mut StakingPool,
        ticket: LiquidTicket,
        unstake_amount: u64,
        now: u64
    ): LiquidTicket {
        let user = TxContext::sender(ctx);
        // Ensure that the caller is the owner of the ticket.
        assert!(ticket.owner == user, 1);
        // Ensure that the lock period has expired.
        assert!(now >= ticket.lock_until, 2);
        // Ensure that the unstake amount does not exceed the ticket amount.
        assert!(unstake_amount <= ticket.amount, 3);
        // Adjust the pool's total staked amount.
        pool.total_staked = pool.total_staked - unstake_amount;
        let remaining = ticket.amount - unstake_amount;
        // Return an updated ticket. If the entire amount was unstaked, the ticket will reflect 0 staked.
        LiquidTicket {
            id: ticket.id,
            owner: user,
            amount: remaining,
            lock_until: ticket.lock_until,
        }
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////////
    // Function: delegate
    //
    // Allows the pool's admin to delegate a specified amount of staked SUI to a validator.
    // The function either updates an existing delegation record or creates a new one.
    //
    // Parameters:
    // - ctx: Transaction context used to retrieve the caller's address.
    // - pool: A mutable reference to the staking pool.
    // - validator: The address of the validator to delegate to.
    // - delegation_amount: The amount of SUI to delegate.
    ////////////////////////////////////////////////////////////////////////////////////////////////////
    public fun delegate(
        ctx: &mut TxContext,
        pool: &mut StakingPool,
        validator: address,
        delegation_amount: u64
    ): () {
        let caller = TxContext::sender(ctx);
        // Only the pool admin can perform delegation.
        assert!(caller == pool.admin, 4);
        let len = vector::length(&pool.delegations);
        let found = false;
        let i = 0;
        while (i < len) {
            let d_ref = vector::borrow_mut(&mut pool.delegations, i);
            if (d_ref.validator == validator) {
                d_ref.amount = d_ref.amount + delegation_amount;
                // Mark that delegation was found and updated.
                found = true;
                break;
            };
            i = i + 1;
        };
        // If no existing delegation record was found, create a new one.
        if (!found) {
            let new_delegation = Delegation { validator, amount: delegation_amount };
            vector::push_back(&mut pool.delegations, new_delegation);
        }
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////////
    // Function: distribute_rewards
    //
    // Allows the pool's admin to distribute rewards to the staking pool.
    // The accrued rewards are added to the pool's total rewards.
    //
    // Parameters:
    // - ctx: Transaction context used to retrieve the caller's address.
    // - pool: A mutable reference to the staking pool.
    // - rewards_amount: The amount of rewards to distribute.
    ////////////////////////////////////////////////////////////////////////////////////////////////////
    public fun distribute_rewards(
        ctx: &mut TxContext,
        pool: &mut StakingPool,
        rewards_amount: u64
    ): () {
        let caller = TxContext::sender(ctx);
        // Only the pool admin can distribute rewards.
        assert!(caller == pool.admin, 5);
        pool.total_rewards = pool.total_rewards + rewards_amount;
    }
}
}