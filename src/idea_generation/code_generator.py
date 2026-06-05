"""
代码生成器模块

基于实验计划自动生成实验代码框架，支持多种 ML 框架（PyTorch, scikit-learn）。
"""

from dataclasses import dataclass
from typing import List, Dict, Optional

# 基础依赖包
_BASE_REQUIREMENTS: List[str] = [
    "numpy",
    "pandas",
    "matplotlib",
    "seaborn",
    "scikit-learn",
    "torch",
    "torchvision",
    "tqdm"
]

# 实验类型特定依赖
_TYPE_SPECIFIC_REQUIREMENTS: Dict[str, List[str]] = {
    "nlp": ["transformers", "tokenizers"],
    "vision": ["opencv-python", "Pillow"]
}

# 配置文件模板
_CONFIG_TEMPLATE: str = """# Experiment Configuration
experiment_type: {experiment_type}
description: {description}

# Training Parameters
batch_size: 32
epochs: 50
learning_rate: 0.001
optimizer: Adam

# Model Parameters
baselines: {baselines}

# Evaluation
metrics: {metrics}

# Dataset
dataset_requirements: {dataset_requirements}
"""


@dataclass
class GeneratedCode:
    """生成的代码数据类
    
    Attributes:
        training_script: 训练脚本代码
        config_file: 配置文件内容
        requirements: 依赖包列表（换行分隔）
        experiment_type: 实验类型
    """
    training_script: str
    config_file: str
    requirements: str
    experiment_type: str
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"GeneratedCode(type='{self.experiment_type}', "
                f"script_len={len(self.training_script)}, "
                f"config_len={len(self.config_file)})")


class CodeGenerator:
    """代码生成器
    
    基于实验计划自动生成实验代码框架，根据实验类型生成对应的代码模板。
    当前为模板-based 实现，后续可接入 LLM 生成更灵活的代码。
    """
    
    def __init__(self) -> None:
        """初始化代码生成器"""
        pass
    
    def generate_code(self, plan: 'ExperimentPlan') -> GeneratedCode:
        """基于实验计划生成完整代码
        
        Args:
            plan: 实验计划
            
        Returns:
            生成的代码对象
        """
        return GeneratedCode(
            training_script=self.generate_training_script(plan),
            config_file=self.generate_config(plan),
            requirements=self.generate_requirements(plan),
            experiment_type=plan.experiment_type
        )
    
    def generate_training_script(self, plan: 'ExperimentPlan') -> str:
        """生成训练脚本
        
        Args:
            plan: 实验计划
            
        Returns:
            训练脚本代码
        """
        # 根据实验类型生成不同的代码模板
        generator_map = {
            "classification": self._generate_classification_script,
            "nlp": self._generate_nlp_script,
            "vision": self._generate_vision_script,
            "regression": self._generate_regression_script,
        }
        
        generator = generator_map.get(plan.experiment_type, self._generate_generic_script)
        return generator(plan)
    
    def generate_config(self, plan: 'ExperimentPlan') -> str:
        """生成配置文件
        
        Args:
            plan: 实验计划
            
        Returns:
            配置文件内容（YAML 格式）
        """
        return _CONFIG_TEMPLATE.format(
            experiment_type=plan.experiment_type,
            description=plan.description,
            baselines=', '.join(plan.baselines),
            metrics=', '.join(plan.metrics),
            dataset_requirements=plan.dataset_requirements
        )
    
    def generate_requirements(self, plan: 'ExperimentPlan') -> str:
        """生成依赖文件
        
        Args:
            plan: 实验计划
            
        Returns:
            依赖包列表（每行一个包）
        """
        requirements = set(_BASE_REQUIREMENTS)
        
        # 添加实验类型特定的依赖
        type_requirements = _TYPE_SPECIFIC_REQUIREMENTS.get(plan.experiment_type, [])
        requirements.update(type_requirements)
        
        return "\n".join(sorted(requirements))
    
    def _generate_classification_script(self, plan: 'ExperimentPlan') -> str:
        """生成分类任务脚本"""
        return '''import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
import matplotlib.pyplot as plt

# Define the model
class ClassificationModel(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(ClassificationModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x

# Training function
def train_model(model, train_loader, criterion, optimizer, epochs=50):
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch_data, batch_labels in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_data)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(train_loader):.4f}")

# Testing function
def test_model(model, test_loader):
    model.eval()
    predictions = []
    true_labels = []
    with torch.no_grad():
        for batch_data, batch_labels in test_loader:
            outputs = model(batch_data)
            _, predicted = torch.max(outputs, 1)
            predictions.extend(predicted.cpu().numpy())
            true_labels.extend(batch_labels.cpu().numpy())
    
    accuracy = accuracy_score(true_labels, predictions)
    f1 = f1_score(true_labels, predictions, average='weighted')
    print(f"Test Accuracy: {accuracy:.4f}, F1-Score: {f1:.4f}")
    return accuracy, f1

# Dataset class
class CustomDataset(Dataset):
    def __init__(self, data, labels):
        self.data = data
        self.labels = labels
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]

# Main execution
if __name__ == "__main__":
    # Load dataset
    print("Loading dataset...")
    # TODO: Implement dataset loading
    
    # Initialize model
    model = ClassificationModel(input_dim=100, num_classes=10)
    
    # Setup training
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Train and test
    # TODO: Create data loaders
    # train_model(model, train_loader, criterion, optimizer)
    # test_model(model, test_loader)
    print("Training script ready.")
'''
    
    def _generate_nlp_script(self, plan: 'ExperimentPlan') -> str:
        """生成 NLP 任务脚本"""
        return '''import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
from sklearn.metrics import accuracy_score
import matplotlib.pyplot as plt

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")

# Text processing function
def tokenize_text(texts, max_length=512):
    return tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt"
    )

# Training function
def train_nlp_model(model, train_data, optimizer, epochs=10):
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch in train_data:
            optimizer.zero_grad()
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_data):.4f}")

# Main execution
if __name__ == "__main__":
    print("NLP experiment ready.")
    print("Model loaded:", model.__class__.__name__)
    # TODO: Implement training loop
'''
    
    def _generate_vision_script(self, plan: 'ExperimentPlan') -> str:
        """生成视觉任务脚本"""
        return '''import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import cv2
import numpy as np

# Define CNN model
class VisionModel(nn.Module):
    def __init__(self, num_classes=10):
        super(VisionModel, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.fc2 = nn.Linear(128, num_classes)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = x.view(-1, 64 * 8 * 8)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x

# Image transforms
transform = transforms.Compose([
    transforms.Resize((32, 32)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

# Main execution
if __name__ == "__main__":
    print("Vision experiment ready.")
    model = VisionModel(num_classes=10)
    print("Model:", model.__class__.__name__)
    # TODO: Load dataset and train
'''
    
    def _generate_regression_script(self, plan: 'ExperimentPlan') -> str:
        """生成回归任务脚本"""
        return '''import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

# Define regression model
class RegressionModel(nn.Module):
    def __init__(self, input_dim):
        super(RegressionModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# Main execution
if __name__ == "__main__":
    print("Regression experiment ready.")
    # TODO: Implement regression training
'''
    
    def _generate_generic_script(self, plan: 'ExperimentPlan') -> str:
        """生成通用脚本"""
        return f'''import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score

# Generic experiment script
print("Generic experiment ready.")
print("Experiment type:", "{plan.experiment_type}")

# TODO: Implement experiment logic
'''
