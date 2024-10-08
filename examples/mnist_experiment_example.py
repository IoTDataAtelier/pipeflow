from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, f1_score
from atelierflow import BaseModel, Experiments, BaseMetric, Dataset

class SKLearnModel(BaseModel):
    def __init__(self, model, fit_params=None, predict_params=None):
        self.model = model
        self.fit_params = fit_params or {}
        self.predict_params = predict_params or {}

    def fit(self, X, y, **kwargs):
        self.model.fit(X, y, **kwargs)

    def predict(self, X, **kwargs):
        return self.model.predict(X, **kwargs)
    
    def get_parameters_description(self):
        return {
            "learning_rate": "1e-10", 
            "epoch": "100",
            "model_version": "1.0"
        }

    def get_fit_params(self):
        return self.fit_params
    
    def get_predict_params(self):
        return self.predict_params

    def requires_supervised_data(self):
        return True

class AccuracyMetric(BaseMetric):
    def __init__(self, name=None, compute_params=None):
        super().__init__(name, compute_params)

    def compute(self, y_true, y_pred, **kwargs):
        return accuracy_score(y_true, y_pred)
  
    def get_compute_params(self):
        return super().get_compute_params()

class F1Metric(BaseMetric):
    def __init__(self, name=None, compute_params=None):
        super().__init__(name, compute_params)

    def compute(self, y_true, y_pred, *kwargs):
        return f1_score(y_true, y_pred, average="weighted")
  
    def get_compute_params(self):
        return super().get_compute_params()

def main():
    # Load the MNIST dataset
    mnist = fetch_openml("mnist_784")
    X = mnist.data
    y = mnist.target.astype(int)  # Convert to integers if needed

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Define the Avro schema for saving results
    avro_schema = {
        "namespace": "example.avro",
        "type": "record",
        "name": "ModelResult",
        "fields": [
            {"name": "model_name", "type": "string"},
            {"name": "metric_name", "type": "string"},
            {"name": "metric_value", "type": "float"},
            {"name": "model_version", "type": "string", "default": "null"},
            {"name": "date", "type": "string"},
            {"name": "dataset_train", "type": "string"},
            {"name": "dataset_test", "type": "string"},
            {"name": "learning_rate", "type": "string"},
            {"name": "epoch", "type": "string"},
        ],
    }

    # Create experiments
    exp = Experiments(avro_schema=avro_schema)

    # Add models to the experiment with fit_params and predict_params
    exp.add_model(SKLearnModel(DecisionTreeClassifier()))

    # Add metrics to the experiment
    exp.add_metric(AccuracyMetric(name="accuracy"))
    exp.add_metric(F1Metric(name='f1'))

    # Create the datasets
    train_set1 = Dataset("dataset_train_1", X_train=X_train, y_train=y_train)
    test_set1 = Dataset("dataset_test_1", X_test=X_test, y_test=y_test)

    # Add datasets to the experiment
    exp.add_train(train_set1)
    exp.add_test(test_set1)

    # Run experiments and save results to Avro
    exp.run("examples/experiment_results.avro")

if __name__ == "__main__":
    main()
