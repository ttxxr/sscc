import torch
from torch import nn
from torch.nn import init


class MultHeadEA(nn.Module):
    def __init__(self, input_size, drop, num_heads, coef=4):
        super().__init__()
        self.num_heads = num_heads
        self.coef = coef
        self.input_size = input_size
        self.k = 1024  # hidden_size - 64 / S（1024） = k(128) * H(8)

        self.trans_dim = nn.Linear(self.input_size, self.input_size*self.coef)
        self.num_heads = self.num_heads * self.coef

        self.Mk = nn.Linear(self.input_size * self.coef // self.num_heads, self.k, bias=False)
        self.Mv = nn.Linear(self.k, self.input_size * self.coef // self.num_heads, bias=False)

        self.attn_drop = nn.Dropout(drop)
        self.proj = nn.Linear(self.input_size * self.coef, self.input_size)
        self.proj_drop = nn.Dropout(drop)

        self.softmax = nn.Softmax(dim=-2)

        self.init_weights()

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                init.kaiming_normal_(m.weight, mode='fan_out')
                if m.bias is not None:
                    init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                init.constant_(m.weight, 1)
                init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                init.normal_(m.weight, std=0.001)
                if m.bias is not None:
                    init.constant_(m.bias, 0)

    def forward(self, x):
        b, n = x.shape
        x = self.trans_dim(x)
        x = x.view(b, n, self.num_heads, -1).permute(0, 2, 1, 3)

        attn = self.Mk(x)
        attn = self.softmax(attn)
        attn = attn / (1e-9 + attn.sum(dim=-1, keepdim=True))  # norm
        attn = self.attn_drop(attn)

        x = self.Mv(attn).permute(0, 2, 1, 3).view(b, n, -1)
        proj = self.proj(x)
        proj = self.proj_drop(proj)

        return proj