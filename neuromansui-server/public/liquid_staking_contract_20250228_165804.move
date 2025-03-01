module temp_addr::my_module {

    // Import necessary modules from the Sui framework.
    use sui::tx_context::TxContext;
    use sui::object::UID;
    use sui::object::uid;

    ////////////////////////////////////////////////////////////////////////////
    //                             Error Codes                                //
    ////////////////////////////////////////////////////////////////////////////

    // Error code for attempting to unstake before the lock period expires.
    const ELOCKED: u64 = 1;
    // Error code when an operation is attempted by a non-owner.
    const E_NOT_OWNER: u64 = 2;
    // Error code for providing an insufficient deposit amount.
    const E_INSUFFICIENT_AMOUNT: u64 = 3;

    ////////////////////////////////////////////////////////////////////////////
    //                             Data Structures                            //
    ////////////////////////////////////////////////////////////////////////////

    // Global configuration resource for the staking pool.
    // Objects published on-chain must have the `key` and `store` abilities.
    public struct Config has key, store {
        id: UID,              // Unique identifier for the configuration object.
        admin: address,       // Administrator of the staking pool.
        reward_rate: u64,     // Reward rate per second.
        lock_period: u64,     // Default lock period (in seconds) for staked funds.
    }

    // Resource representing an individual user's staked position.
    public struct StakedPosition has key, store {
        id: UID,                      // Unique identifier for the position.
        owner: address,               // Owner of the staked position.
        deposit: u64,                 // Amount staked (in SUI units).
        last_update: u64,             // Timestamp of the last rewards update.
        lock_until: u64,              // Timestamp until which unstaking remains locked.
        delegated_validator: address, // The validator to which the stake is delegated.
    }

    // Resource representing the liquid staking token.
    // This token is minted when a user stakes, representing a tradable share of the stake.
    public struct LiquidStakedToken has key, store {
        id: UID,         // Unique identifier for the token.
        owner: address,  // Owner of the liquid token.
        amount: u64,     // The staked amount represented by this token.
    }

    ////////////////////////////////////////////////////////////////////////////
    //                          Native Publishing Function                    //
    ////////////////////////////////////////////////////////////////////////////

    // Native function to publish an object to an account.
    // The Move framework provides an intrinsic implementation.
    native public fun move_to<T: store>(acc: &signer, obj: T);

    ////////////////////////////////////////////////////////////////////////////
    //                          Initialization Function                       //
    ////////////////////////////////////////////////////////////////////////////

    // Entry function to initialize the staking pool configuration.
    // The caller becomes the administrator.
    public entry fun init_config(admin: &signer, reward_rate: u64, lock_period: u64, ctx: &mut TxContext) {
        let config_uid = uid::new(ctx);
        // In Sui Move, the admin's address is inferred from the transaction context.
        let admin_addr = TxContext::sender(ctx);
        let config = Config {
            id: config_uid,
            admin: admin_addr,
            reward_rate,
            lock_period,
        };
        move_to(admin, config);
    }

    ////////////////////////////////////////////////////////////////////////////
    //                          Staking Functionality                         //
    ////////////////////////////////////////////////////////////////////////////

    // Stake function:
    // Allows a user to stake a specified deposit and delegate to a chosen validator.
    // Parameters:
    // - _staker: The signer initiating the stake.
    // - deposit: The amount to stake.
    // - delegate: The validator's address.
    // - lock: If true, the staked funds are locked for the configured period.
    // - current_time: The current timestamp.
    // - config: Reference to the global configuration.
    // - ctx: Transaction context for UID generation.
    // Returns:
    // - A new StakedPosition resource.
    // - A LiquidStakedToken representing the staked amount.
    public fun stake(
        _staker: &signer,
        deposit: u64,
        delegate: address,
        lock: bool,
        current_time: u64,
        config: &Config,
        ctx: &mut TxContext
    ): (StakedPosition, LiquidStakedToken) {
        check(deposit > 0, E_INSUFFICIENT_AMOUNT);
        let owner = TxContext::sender(ctx);
        let lock_until = if (lock) { current_time + config.lock_period } else { current_time };
        let pos_uid = uid::new(ctx);
        let position = StakedPosition {
            id: pos_uid,
            owner,
            deposit,
            last_update: current_time,
            lock_until,
            delegated_validator: delegate,
        };
        let liq_uid = uid::new(ctx);
        let liquid = LiquidStakedToken {
            id: liq_uid,
            owner,
            amount: deposit,
        };
        (position, liquid)
    }

    // Internal helper to accrue rewards.
    // Computes rewards based on the elapsed time since the last update.
    fun accrue_rewards(position: &mut StakedPosition, current_time: u64, reward_rate: u64): u64 {
        let elapsed = current_time - position.last_update;
        let reward = elapsed * reward_rate;
        position.last_update = current_time;
        reward
    }

    // Claim rewards function:
    // Allows the owner of a staked position to claim accrued rewards without unstaking.
    // Parameters:
    // - _staker: The signer claiming rewards.
    // - position: Mutable reference to the staked position.
    // - current_time: The current timestamp.
    // - config: Reference to the global configuration.
    // - ctx: Transaction context to determine the caller.
    // Returns: The accrued reward amount.
    public fun claim_rewards(
        _staker: &signer,
        position: &mut StakedPosition,
        current_time: u64,
        config: &Config,
        ctx: &mut TxContext
    ): u64 {
        let caller = TxContext::sender(ctx);
        check(caller == position.owner, E_NOT_OWNER);
        let reward = accrue_rewards(position, current_time, config.reward_rate);
        reward
    }

    ////////////////////////////////////////////////////////////////////////////
    //                          Unstaking Functionality                       //
    ////////////////////////////////////////////////////////////////////////////

    // Unstake function:
    // Allows a user to redeem their staked funds along with accrued rewards.
    // Preconditions:
    // - The caller must own both the staked position and associated liquid token.
    // - The current time must be at or after the lock_until timestamp.
    // Consumes the position and token.
    // Returns: The total amount (deposit plus accrued rewards).
    public fun unstake(
        _staker: &signer,
        position: StakedPosition,
        liquid: LiquidStakedToken,
        current_time: u64,
        config: &Config,
        ctx: &mut TxContext
    ): u64 {
        let caller = TxContext::sender(ctx);
        check(caller == position.owner, E_NOT_OWNER);
        check(caller == liquid.owner, E_NOT_OWNER);
        check(current_time >= position.lock_until, ELOCKED);
        let reward = (current_time - position.last_update) * config.reward_rate;
        let total_amount = position.deposit + reward;
        total_amount
    }

    ////////////////////////////////////////////////////////////////////////////
    //                          Helper Function                               //
    ////////////////////////////////////////////////////////////////////////////

    // Utility function to check conditions and abort with a given error code if false.
    fun check(condition: bool, error_code: u64) {
        if (!condition) {
            abort error_code;
        }
    }
}