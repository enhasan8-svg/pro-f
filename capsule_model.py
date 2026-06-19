import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models

# --- [1] طبقات مساعدة ---
class StatsNet(nn.Module):
    def forward(self, x):
        # x shape: [B, C, H, W] -> flatten H, W to [B, C, H*W]
        x = x.view(x.shape[0], x.shape[1], x.shape[2] * x.shape[3])
        return torch.stack((torch.mean(x, 2), torch.std(x, 2)), dim=1)

class View(nn.Module):
    def __init__(self, *shape):
        super().__init__()
        self.shape = shape
    def forward(self, x):
        return x.view(self.shape[0], *self.shape[1:])  # Safe view handling batch dim

# --- [2] مستخرج الميزات ---
class EfficientNetExtractor(nn.Module):
    """
    يستخدم EfficientNet-B3 لاستخراج feature maps
    من أول 4 مراحل فقط → [B, 48, H, W]
    أوزانه من ImageNet — مجمّد بالكامل لا يتدرب
    """
    def __init__(self):
        super().__init__()
        # We load without weights by default, as we will load the trained state_dict anyway.
        # But we initialize the structure using efficientnet_b3.
        backbone = models.efficientnet_b3(weights=None)
        self.features = nn.Sequential(
            *list(backbone.features.children())[0:4]
        )
    def forward(self, x):
        return self.features(x)

# --- [3] معمارية الكبسولات ---
class FeatureExtractor(nn.Module):
    def __init__(self, view_size=8):
        super().__init__()
        self.capsules = nn.ModuleList([
            nn.Sequential(
                nn.Conv2d(48, 64, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(),
                nn.Conv2d(64, 16, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(16),
                nn.ReLU(),
                StatsNet(),
                nn.Conv1d(2, 8, kernel_size=5, stride=2, padding=2),
                nn.BatchNorm1d(8),
                nn.Conv1d(8, 1, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm1d(1),
                View(-1, view_size),
            ) for _ in range(3)
        ])

    def forward(self, x):
        outputs = [cap(x) for cap in self.capsules]
        output  = torch.stack(outputs, dim=-1)
        norm_sq = (output ** 2).sum(dim=-1, keepdim=True)
        scale   = norm_sq / (1 + norm_sq)
        return scale * output / torch.sqrt(norm_sq + 1e-8)

# --- [4] طبقة الـ Dynamic Routing ---
class RoutingLayer(nn.Module):
    def __init__(self, num_input_capsules, num_output_capsules,
                 data_in, data_out, num_iterations=2):
        super().__init__()
        self.num_iterations = num_iterations
        self.route_weights  = nn.Parameter(
            torch.randn(num_output_capsules, num_input_capsules,
                        data_out, data_in)
        )

    def forward(self, x, random=False, dropout=0.0):
        x      = x.transpose(2, 1)
        priors = self.route_weights[:, None] @ x[None, :, :, :, None]
        priors = priors.transpose(1, 0)
        logits = torch.zeros_like(priors)
        for i in range(self.num_iterations):
            probs   = F.softmax(logits, dim=2)
            outputs = (probs * priors).sum(dim=2, keepdim=True)
            if i < self.num_iterations - 1:
                logits = logits + priors * outputs
        return outputs.squeeze(-1).squeeze(2).transpose(2, 1).contiguous()

# --- [5] الموديل النهائي ---
class CapsuleNet(nn.Module):
    def __init__(self, num_class=2, view_size=8):
        super().__init__()
        self.fea_ext       = FeatureExtractor(view_size)
        self.routing_stats = RoutingLayer(
            num_input_capsules=3,
            num_output_capsules=num_class,
            data_in=view_size,
            data_out=4
        )

    def forward(self, x, random=False, dropout=0.0):
        z       = self.fea_ext(x)
        z       = self.routing_stats(z, random, dropout)
        classes = F.softmax(z, dim=-1)
        return z, classes.detach().mean(dim=1)

# helper function to load both modules and restore the full trained model
def load_deepfake_model(model_path="final_model_99.pt", device="cpu"):
    eff_ext = EfficientNetExtractor().to(device)
    capnet = CapsuleNet(num_class=2, view_size=8).to(device)
    
    checkpoint = torch.load(model_path, map_location=device)
    
    # Load state dicts
    eff_ext.load_state_dict(checkpoint['eff_ext_state'])
    capnet.load_state_dict(checkpoint['model_state'])
    
    eff_ext.eval()
    capnet.eval()
    
    return eff_ext, capnet
