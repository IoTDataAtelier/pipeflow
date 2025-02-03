from fastavro import writer
import numpy as np
from sklearn.model_selection import KFold
from mtsa.utils import files_train_test_split
from atelierflow.utils.modelFactory import ModelFactory
from atelierflow.steps.step import Step

class LoadDataStep(Step):
    def process(self, element):
        X_train, X_test, y_train, y_test = files_train_test_split(element['path'])
      
        yield {
            'X_train': X_train,
            'X_test': X_test,
            'y_train': y_train,
            'y_test': y_test,
            'model_class': element['models'][0],
            'model_kwargs': element['model_kwargs'],
            'metric': element['metrics'][0],
            'learning_rate_values': element['learning_rate_values'],
            'batch_size_values': element['batch_size_values']
        }

    def name(self):
        return "LoadDataStep"

class PrepareFoldsStep(Step):
    def process(self, element):
        X_train = element['X_train']
        y_train = element['y_train']

        kf = KFold(n_splits=5)
        splits = list(enumerate(kf.split(X_train, y_train)))
        element['splits'] = splits
        yield element

    def name(self):
        return "PrepareFoldsStep"

class TrainModelStep(Step):
    def process(self, element):

        X_train = element['X_train']
        y_train = element['y_train']

        model_class = element['model_class']
        model_kwargs = element['model_kwargs']
        
        for learning_rate in element['learning_rate_values']:
            for batch_size in element['batch_size_values']:
                print('\nlr= {}, batch= {}\n'.format(learning_rate, batch_size))
                for fold, (train_index, val_index) in element['splits']:
                    print(f"Fold: {fold + 1}")

                    x_train_fold, y_train_fold = X_train[train_index], y_train[train_index]
                    model = ModelFactory.create_model(model_class, **model_kwargs)
                    model.fit(x_train_fold, y_train_fold, batch_size=int(batch_size), learning_rate=learning_rate, epochs=2)
                    element['sampling_rate'] = model.sampling_rate
                    element['model'] = model
                    element['batch_size'] = batch_size
                    element['learning_rate'] = learning_rate
                    yield element
                    del model

    def name(self):
        return "TrainModelStep"

class EvaluateModelStep(Step):
    def process(self, element):
        model = element['model']
        X_test = element['X_test']
        y_test = element['y_test']
        metric = element['metric']

        auc = metric.compute(model, X_test, y_test)
        element['AUC_ROC'] = auc
        yield element

    def name(self):
        return "EvaluateModelStep"

class AppendResultsStep(Step):
    def __init__(self, output_path, avro_schema):
        self.output_path = output_path
        self.avro_schema = avro_schema

    def process(self, element):
        batch_size = element['batch_size']
        epoch_size = '20'
        learning_rate = element['learning_rate']
        sampling_rate = element['sampling_rate']
        AUC_ROCs = element['AUC_ROC']
        model = element['model']

        print(f"  -> Appending results for model {type(model).__name__} to Avro file...\n")

        record = {
            "batch_size": str(batch_size),
            "epoch_size": str(epoch_size),
            "learning_rate": str(learning_rate),
            "sampling_rate": str(sampling_rate),
            "AUC_ROCs": str(AUC_ROCs)
        }
        with open(self.output_path, "a+b") as out:
            writer(out, self.avro_schema, [record])

        yield element

    def name(self):
        return "AppendResultsStep"


