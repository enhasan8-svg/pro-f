import torch
import sys

def inspect():
    model_path = "final_model_99.pt"
    print(f"Inspecting {model_path}...")
    try:
        # Try loading as a full model or state_dict
        data = torch.load(model_path, map_location=torch.device('cpu'))
        print("Successfully loaded with torch.load!")
        print("Type of loaded object:", type(data))
        if isinstance(data, dict):
            print("It is a state_dict or dictionary. Keys:")
            for k in data.keys():
                val = data[k]
                if isinstance(val, dict) or str(type(val)).endswith("OrderedDict'>"):
                    print(f"  {k}: dict/OrderedDict with {len(val)} parameters")
                    print(f"    Sample parameter keys: {list(val.keys())[:5]}")
                else:
                    print(f"  {k}: type {type(val)}, value: {val}")
        else:
            print("It is a model object. Structure:")
            print(data)
    except Exception as e1:
        print(f"Failed loading with torch.load: {e1}")
        try:
            # Try loading as TorchScript
            data = torch.jit.load(model_path, map_location=torch.device('cpu'))
            print("Successfully loaded as TorchScript!")
            print(data)
            print("Model code:")
            print(data.code)
        except Exception as e2:
            print(f"Failed loading as TorchScript: {e2}")

if __name__ == "__main__":
    inspect()
