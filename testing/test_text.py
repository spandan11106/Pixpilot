from data_processing.text import process_markdown
import os 
import re 

if __name__ == "__main__":
    test_dir = "./testing_input"
    test_file = f"{test_dir}/sample_input.md"
    
    os.makedirs(test_dir, exist_ok=True)
    
    mock_input = (
        "# Skeleton Watch Core\n\n"
        "Check out our new launch at https://luxury-time.com/drop1.\n\n"
        "This features a [Polished Gold Bezel](https://luxury-time.com/specs/gold) "
        "and a premium black leather strap. Visit www.clocks.io for manual details."
    )
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(mock_input)
        
    try:
        result = process_markdown(test_file)
        print(f"✅ Extracted Content:\n")
        print(result['content'])
    except Exception as e:
        print(f"❌ Error: {e}")
