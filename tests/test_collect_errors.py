import textwrap
from gymnasuium.prompt_loader import collect_errors

def test_collect_errors():
    sample_output = textwrap.dedent("""\
        UPDATING GIT DEPENDENCY https://github.com/ronanyeah/time-locked-balance.git
        INCLUDING DEPENDENCY TimeLockedBalance
        INCLUDING DEPENDENCY Sui
        INCLUDING DEPENDENCY MoveStdlib
        BUILDING Mineral
        [
          {
            "file": "./sources/mine.move",
            "line": 47,
            "column": 12,
            "level": "NonblockingError",
            "category": 5,
            "code": 1,
            "msg": "ability constraint not satisfied"
          },
          {
            "file": "./sources/mine.move",
            "line": 50,
            "column": 18,
            "level": "NonblockingError",
            "category": 5,
            "code": 1,
            "msg": "ability constraint not satisfied"
          },
          {
            "file": "./sources/mine.move",
            "line": 70,
            "column": 12,
            "level": "NonblockingError",
            "category": 5,
            "code": 1,
            "msg": "ability constraint not satisfied"
          },
          {
            "file": "./sources/mine.move",
            "line": 70,
            "column": 12,
            "level": "NonblockingError",
            "category": 5,
            "code": 1,
            "msg": "ability constraint not satisfied"
          },
          {
            "file": "./sources/mine.move",
            "line": 434,
            "column": 8,
            "level": "Warning",
            "category": 4,
            "code": 2,
            "msg": "unnecessary 'while (true)', replace with 'loop'"
          },
          {
            "file": "./sources/icon.move",
            "line": 6,
            "column": 8,
            "level": "Warning",
            "category": 4,
            "code": 4,
            "msg": "unneeded return"
          },
          {
            "file": "/Users/kz/.move/https___github_com_MystenLabs_sui_git_mainnet-v1.24.1/crates/sui-framework/packages/sui-framework/sources/object.move",
            "line": 165,
            "column": 4,
            "level": "Warning",
            "category": 1,
            "code": 4,
            "msg": "invalid documentation comment"
          }
        ]
        Failed to build Move modules: Compilation error.
    """)
    
    errors_by_code = collect_errors(sample_output)
    
    # Expected groups:
    # - NonblockingError (code 1, category 5) → "N01005": 4 errors
    # - Warning (code 2, category 4) → "W02004": 1 error
    # - Warning (code 4, category 4) → "Lint W04004": 1 error (prefixed with "Lint " when code is 4)
    # - Warning (code 4, category 1) → "Lint W04001": 1 error
    
    assert "N01005" in errors_by_code, "Expected group 'N01005' is missing"
    assert len(errors_by_code["N01005"]) == 4, "Expected 4 errors in group 'N01005'"
    
    assert "W02004" in errors_by_code, "Expected group 'W02004' is missing"
    assert len(errors_by_code["W02004"]) == 1, "Expected 1 error in group 'W02004'"
    
    assert "Lint W04004" in errors_by_code, "Expected group 'Lint W04004' is missing"
    assert len(errors_by_code["Lint W04004"]) == 1, "Expected 1 error in group 'Lint W04004'"
    
    assert "Lint W04001" in errors_by_code, "Expected group 'Lint W04001' is missing"
    assert len(errors_by_code["Lint W04001"]) == 1, "Expected 1 error in group 'Lint W04001'"
    
    assert len(errors_by_code) == 4, "Expected a total of 4 error groups" 