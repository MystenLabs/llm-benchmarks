module 0x2::TempContract {

    // Import necessary modules from Sui and MoveStdlib.
    use sui::account;
    use sui::object::{UID};
    use sui::transfer;
    use sui::tx_context::TxContext;
    use move_stdlib::object::{move_to, exists, borrow_global};

    ////////////////////////////////////////////////////////////////////////
    // Admin Structure
    //
    // This structure represents an administrator account that is allowed
    // to mint and burn tokens. It is stored in global storage and includes a
    // unique identifier (UID) and the administrator’s address.
    ////////////////////////////////////////////////////////////////////////
    struct Admin has key, store {
        id: UID,
        admin: address,
    }

    ////////////////////////////////////////////////////////////////////////
    // Coin Structure
    //
    // This structure represents the custom token. It includes a unique
    // identifier and a value. The 'drop' ability is added to allow burning
    // (i.e. dropping) tokens.
    ////////////////////////////////////////////////////////////////////////
    struct Coin has key, store, drop {
        id: UID,
        value: u64,
    }

    ////////////////////////////////////////////////////////////////////////
    // Function: init_admin
    //
    // This function is used to initialize an admin account.
    // The account deploying the Admin object is recorded as the administrator.
    //
    // Parameters:
    // - account: Signer representing the admin account.
    // - _ctx: A mutable reference to the transaction context used for UID generation.
    ////////////////////////////////////////////////////////////////////////
    public fun init_admin(account: &signer, _ctx: &mut TxContext) {
        let admin_addr = account::address_of(account);
        let admin_obj = Admin { id: UID::new(_ctx), admin: admin_addr };
        move_to(account, admin_obj);
    }

    ////////////////////////////////////////////////////////////////////////
    // Function: mint
    //
    // This function mints a new Coin token. It requires that the caller
    // is an admin. The minted token has the specified amount as its value.
    //
    // Parameters:
    // - admin: Signer representing the admin account.
    // - amount: The value assigned to the newly minted token.
    // - _ctx: A mutable reference to the transaction context used for UID generation.
    //
    // Returns:
    // - Coin: The newly minted token.
    ////////////////////////////////////////////////////////////////////////
    public fun mint(admin: &signer, amount: u64, _ctx: &mut TxContext): Coin {
        let caller = account::address_of(admin);
        // Check that an Admin object exists at the caller's address.
        assert!(exists<Admin>(caller), 1);
        let _admin_obj = borrow_global<Admin>(caller);
        Coin { id: UID::new(_ctx), value: amount }
    }

    ////////////////////////////////////////////////////////////////////////
    // Function: burn
    //
    // This function burns (destroys) a Coin token. It requires that the caller
    // is an admin. Burning is achieved by letting the token go out of scope,
    // utilizing the 'drop' ability.
    //
    // Parameters:
    // - admin: Signer representing the admin account.
    // - coin: The token to be burned.
    // - _ctx: A mutable reference to the transaction context (unused, but kept
    //         for signature consistency).
    ////////////////////////////////////////////////////////////////////////
    public fun burn(admin: &signer, coin: Coin, _ctx: &mut TxContext) {
        let caller = account::address_of(admin);
        // Confirm admin privileges before allowing the burn.
        assert!(exists<Admin>(caller), 3);
        let _admin_obj = borrow_global<Admin>(caller);
        // Since Coin has the 'drop' ability, simply letting 'coin' go out of scope
        // effectively burns it.
        coin;
    }

    ////////////////////////////////////////////////////////////////////////
    // Function: transfer
    //
    // This function transfers a Coin token from the sender to the recipient.
    // It utilizes the Sui transfer module to reassign ownership of the token.
    //
    // Parameters:
    // - sender: Signer representing the current owner of the token.
    // - recipient: The address of the new owner.
    // - coin: The token to be transferred.
    ////////////////////////////////////////////////////////////////////////
    public fun transfer(sender: &signer, recipient: address, coin: Coin) {
        // Execute the token transfer.
        transfer::transfer(coin, recipient);
    }
}