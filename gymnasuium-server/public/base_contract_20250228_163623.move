// Module: my_module.move
// This Sui Move module defines a simple token with mint, burn and transfer functions.
// It demonstrates how to create a custom resource (Token) that is a Sui object with unique id assignment.
// Administrative functions (mint and burn) are restricted to the admin address.
// Note: In Sui, when a new object is created via move_to the system automatically assigns its UID.
// Here we initialize the id field with a dummy value (using Default::default()) which is then overwritten.
module 0x0::my_module {

    use std::signer;
    use std::assert;
    use std::default::Default;
    // Import the UID type from the Sui framework.
    use sui::object::UID;

    // The admin address is hardcoded to the module address (0x0) for demonstration.
    const ADMIN: address = @0x0;

    // The Token resource represents a basic token.
    // It is declared with abilities "key" and "store" which is required for Sui objects.
    struct Token has key, store {
        // The 'id' field is of type UID.
        // When created using move_to, the system will assign a unique UID value.
        id: UID,
        balance: u64,
    }

    // Helper function to check if the signer is the admin.
    public fun is_admin(admin: &signer): bool {
        signer::address_of(admin) == ADMIN
    }

    // Mint a new token.
    // Only the admin (whose address is ADMIN) can mint tokens.
    // The token is created with a dummy UID which is replaced by the system,
    // and then moved into the admin's account.
    public fun mint(admin: &signer, amount: u64) {
        // Ensure that only admin can mint tokens.
        assert!(is_admin(admin), 1);
        // Construct a new Token.
        // The 'id' field is initialized with Default::default(); in Sui, move_to will set the proper UID.
        let token = Token { id: Default::default(), balance: amount };
        // Move the token object into the admin's account.
        move_to(admin, token);
    }

    // Burn a token.
    // Only the admin is allowed to burn (destroy) tokens.
    // Consuming the token parameter causes it to be dropped/destroyed.
    public fun burn(admin: &signer, token: Token) {
        // Ensure that only admin can burn tokens.
        assert!(is_admin(admin), 1);
        // When the token goes out of scope, it is effectively destroyed.
        // (In a real implementation, you might want to emit an event or perform additional logic.)
    }

    // Transfer a token.
    // The owner (sender) transfers the token to the recipient by moving the object.
    // Both sender and recipient must provide signer references so that move_to can assign ownership appropriately.
    public fun transfer(sender: &signer, token: Token, recipient: &signer) {
        // Ownership is verified implicitly because the sender must have the token.
        // Transfer the token object from sender's account to recipient's account.
        move_to(recipient, token);
    }
}