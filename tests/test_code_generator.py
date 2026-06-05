"""
测试代码生成器模块
"""
import pytest
from src.idea_generation.code_generator import CodeGenerator, GeneratedCode
from src.idea_generation.experiment_designer import ExperimentPlan


class TestCodeGenerator:
    """测试 CodeGenerator 类"""
    
    def test_create_code_generator(self):
        """测试创建 CodeGenerator 实例"""
        generator = CodeGenerator()
        assert generator is not None
        assert hasattr(generator, 'generate_code')
        assert hasattr(generator, 'generate_training_script')
        assert hasattr(generator, 'generate_config')
        assert hasattr(generator, 'generate_requirements')
    
    def test_generate_training_code(self):
        """测试生成训练代码"""
        generator = CodeGenerator()
        plan = ExperimentPlan(
            baselines=["resnet50", "vgg16"],
            metrics=["accuracy", "f1_score"],
            dataset_requirements="ImageNet subset",
            estimated_duration=120,
            experiment_type="classification",
            description="Test experiment"
        )
        code = generator.generate_code(plan)
        
        assert code is not None
        assert isinstance(code, GeneratedCode)
        assert "import" in code.training_script
        assert "model" in code.training_script.lower()
    
    def test_generated_code_structure(self):
        """测试生成的代码结构"""
        generator = CodeGenerator()
        plan = ExperimentPlan(
            baselines=["Logistic Regression"],
            metrics=["Accuracy"],
            dataset_requirements="Standard dataset",
            estimated_duration=24,
            experiment_type="classification",
            description="Test"
        )
        code = generator.generate_code(plan)
        
        assert code.config_file != ""
        assert code.requirements != ""
        assert "torch" in code.requirements.lower() or "sklearn" in code.requirements.lower()
    
    def test_generate_classification_code(self):
        """测试生成分类任务代码"""
        generator = CodeGenerator()
        plan = ExperimentPlan(
            baselines=["SVM", "Random Forest"],
            metrics=["Accuracy", "F1-Score"],
            dataset_requirements="Labeled data",
            estimated_duration=24,
            experiment_type="classification",
            description="Classification test"
        )
        code = generator.generate_code(plan)
        
        assert "Dataset" in code.training_script or "dataset" in code.training_script
        assert "train" in code.training_script.lower()
        assert "test" in code.training_script.lower()
    
    def test_generate_nlp_code(self):
        """测试生成 NLP 任务代码"""
        generator = CodeGenerator()
        plan = ExperimentPlan(
            baselines=["BERT-base", "LSTM"],
            metrics=["BLEU", "Accuracy"],
            dataset_requirements="Text corpus",
            estimated_duration=48,
            experiment_type="nlp",
            description="NLP test"
        )
        code = generator.generate_code(plan)
        
        assert "tokenizer" in code.training_script.lower() or "transformers" in code.training_script.lower()
    
    def test_generate_vision_code(self):
        """测试生成视觉任务代码"""
        generator = CodeGenerator()
        plan = ExperimentPlan(
            baselines=["ResNet", "VGG"],
            metrics=["mAP", "Accuracy"],
            dataset_requirements="Image dataset",
            estimated_duration=72,
            experiment_type="vision",
            description="Vision test"
        )
        code = generator.generate_code(plan)
        
        assert "image" in code.training_script.lower() or "torchvision" in code.training_script.lower()
    
    def test_generate_requirements_file(self):
        """测试生成依赖文件"""
        generator = CodeGenerator()
        plan = ExperimentPlan(
            baselines=[],
            metrics=[],
            dataset_requirements="",
            estimated_duration=0,
            experiment_type="classification",
            description=""
        )
        code = generator.generate_code(plan)
        
        assert "torch" in code.requirements or "numpy" in code.requirements
        assert "matplotlib" in code.requirements or "seaborn" in code.requirements
    
    def test_generate_config_file(self):
        """测试生成配置文件"""
        generator = CodeGenerator()
        plan = ExperimentPlan(
            baselines=["Baseline1"],
            metrics=["Accuracy"],
            dataset_requirements="Dataset",
            estimated_duration=24,
            experiment_type="classification",
            description="Config test"
        )
        code = generator.generate_code(plan)
        
        assert "batch_size" in code.config_file.lower() or "epochs" in code.config_file.lower()
        assert "learning_rate" in code.config_file.lower() or "lr" in code.config_file.lower()


class TestGeneratedCode:
    """测试 GeneratedCode dataclass"""
    
    def test_create_generated_code(self):
        """测试创建 GeneratedCode 实例"""
        code = GeneratedCode(
            training_script="import torch\nmodel = ...",
            config_file="batch_size: 32\nepochs: 10",
            requirements="torch\nnumpy\nmatplotlib",
            experiment_type="classification"
        )
        
        assert "import torch" in code.training_script
        assert "batch_size" in code.config_file
        assert "torch" in code.requirements
        assert code.experiment_type == "classification"
    
    def test_generated_code_default_values(self):
        """测试默认值"""
        code = GeneratedCode(
            training_script="",
            config_file="",
            requirements="",
            experiment_type=""
        )
        
        assert isinstance(code.training_script, str)
        assert isinstance(code.config_file, str)
        assert isinstance(code.requirements, str)
        assert isinstance(code.experiment_type, str)
    
    def test_generated_code_string_representation(self):
        """测试字符串表示"""
        code = GeneratedCode(
            training_script="test",
            config_file="test",
            requirements="test",
            experiment_type="test"
        )
        
        assert "GeneratedCode" in str(code)
        assert "test" in str(code).lower()
