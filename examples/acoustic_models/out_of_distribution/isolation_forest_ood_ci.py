from fastavro import parse_schema
from atelierflow import BaseModel, ExperimentBuilder
from mtsa.models import IForest  
from examples.acoustic_models.out_of_distribution.isolation_forest_ood_steps_ci import LoadDataStep, PrepareFoldsStep, TrainModelStep, EvaluateModelStep, AssignKeyStep, CalculateConfidenceIntervalStep, AppendResultsStep
import os
from atelierflow.metrics.metric import BaseMetric
from mtsa.metrics import calculate_aucroc
import apache_beam as beam

class IForestModel(BaseModel):
    def __init__(self, model):
        self.model = model

    def fit(self, X, y, **kwargs):
        self.model.fit(X, y, **kwargs)

    def predict(self, X):
        return self.model.predict(X)
    
    def create_new_instance(self, n_estimators, max_features, contamination, max_samples, sampling_rate):
        """
        Cria uma nova instância do IForestModel com os parâmetros fornecidos. (.clone não existe para o isolation)
        """
        new_model = IForest(
            n_estimators=n_estimators,
            max_features=max_features,
            contamination=contamination,
            max_samples=max_samples,
            sampling_rate=sampling_rate
        )
        return IForestModel(model=new_model)
    
class ROCAUC(BaseMetric):
    def __init__(self):
        pass

    def compute(self, model, X, y):
        return calculate_aucroc(model, X, y)
    
def main():
    # Definição do Esquema Avro para salvar os resultados
    avro_schema = {
    "namespace": "example.avro",
    "type": "record",
    "name": "ModelConfidenceResult",
    "fields": [
        {"name": "n_estimators", "type": "string"},
        {"name": "max_features", "type": "string"},
        {"name": "contamination", "type": "string"},
        {"name": "max_samples", "type": "string"},
        {"name": "sampling_rate", "type": "string"},
        {"name": "lower_bound", "type": "float"},
        {"name": "mean_auc", "type": "float"},
        {"name": "upper_bound", "type": "float"},
    ],
}

    # Instanciar o ExperimentBuilder
    builder = ExperimentBuilder()
    builder.set_avro_schema(avro_schema)

    # Definir os parâmetros para o modelo Isolation Forest
    max_features_values = [0.5, 1.0]
    n_estimators_values = [2, 10, 40, 70, 100]

    initial_inputs = {
        "machine_type": "pump",  
        "train_ids": ["id_02", "id_04", "id_06"],
        "test_id": "id_00",
        "models": [IForestModel(model=IForest(
            n_estimators=100,  
            max_features=1.0,
            contamination=0.01,
            max_samples=256,
            sampling_rate=None
        ))],
        "metrics": [ROCAUC()],
        "max_features_values": max_features_values,
        "n_estimators_values": n_estimators_values
    }

    # Adicionar o modelo ao builder
    builder.add_model(initial_inputs['models'][0])

    # Adicionar a métrica AUC ROC
    builder.add_metric(initial_inputs['metrics'][0])

    # Definir o caminho de saída para o arquivo Avro
    output_dir = "/data/joao/pipeflow/examples/isolation_forest_ood_results"
    os.makedirs(output_dir, exist_ok=True)

    # Adicionar os passos do pipeline
    builder.add_step(LoadDataStep())
    builder.add_step(PrepareFoldsStep())
    builder.add_step(TrainModelStep())
    builder.add_step(EvaluateModelStep())
    builder.add_step(AssignKeyStep())
    builder.add_step(beam.GroupByKey())  
    builder.add_step(CalculateConfidenceIntervalStep())
    builder.add_step(AppendResultsStep(output_dir, parse_schema(avro_schema)))

    # Construir o objeto Experiments
    experiments = builder.build()

    # Executar os experimentos com os inputs iniciais
    experiments.run(initial_inputs)

if __name__ == "__main__":
    main()
