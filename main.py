import random
import time
from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import numpy as np


class ServiceCenter:
    def __init__(self, pos):
        self.pos = pos


class Customer(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.time_without_food = 0
        self.is_hungry = False
        self.color = "green"

    def step(self):
        self.time_without_food += 1
        if not self.is_hungry:
            if random.random() < 0.007:
                self.is_hungry = True
                self.color = "red"


class DeliveryPerson(Agent):
    def __init__(self, unique_id, model, service_center):
        super().__init__(unique_id, model)
        self.service_center = service_center
        self.color = "blue"
        self.fed_customers = 0
        self.returning = False

    def step(self):
        if self.returning:
            if self.pos == self.service_center.pos:
                self.returning = False
                self.fed_customers = 0
            else:
                self.move_towards(self.service_center.pos)
        else:
            if self.fed_customers < 5:
                hungry_customers = [agent for agent in self.model.schedule.agents
                                    if isinstance(agent, Customer) and agent.is_hungry]
                if hungry_customers:
                    target = min(hungry_customers,
                                 key=lambda x: self.distance_to(x.pos))
                    if self.pos == target.pos:
                        target.time_without_food = 0
                        target.is_hungry = False
                        target.color = "green"
                        self.fed_customers += 1
                        if self.fed_customers >= 5:
                            self.returning = True
                    else:
                        self.move_towards(target.pos)
            else:
                self.returning = True

    def distance_to(self, pos):
        x1, y1 = self.pos
        x2, y2 = pos
        return abs(x1 - x2) + abs(y1 - y2)

    def move_towards(self, target):
        current_x, current_y = self.pos
        target_x, target_y = target

        if current_x < target_x:
            next_x = current_x + 1
        elif current_x > target_x:
            next_x = current_x - 1
        else:
            next_x = current_x

        if current_y < target_y:
            next_y = current_y + 1
        elif current_y > target_y:
            next_y = current_y - 1
        else:
            next_y = current_y

        new_pos = (next_x, next_y)
        self.model.grid.move_agent(self, new_pos)


class FoodDeliveryModel(Model):
    def __init__(self, Customers=100, N_delivery_persons=6, width=20, height=20):
        self.num_customers = Customers
        self.num_delivery_persons = N_delivery_persons
        self.grid = MultiGrid(width, height, True)
        self.schedule = RandomActivation(self)

        self.service_center_top = ServiceCenter((width // 2, 0))
        self.service_center_bottom = ServiceCenter((width // 2, height - 2))

        self.grid.place_agent(self.service_center_top,
                              self.service_center_top.pos)
        self.grid.place_agent(self.service_center_bottom,
                              self.service_center_bottom.pos)

        available_positions = [(x, y) for x in range(self.grid.width)
                               for y in range(self.grid.height)
                               if (x, y) not in [self.service_center_top.pos, self.service_center_bottom.pos]]
        customer_positions = self.random.sample(
            available_positions, self.num_customers)

        for i in range(self.num_customers):
            customer = Customer(i, self)
            self.grid.place_agent(customer, customer_positions[i])
            self.schedule.add(customer)

        for i in range(self.num_delivery_persons):
            if i % 2 == 0:
                delivery_person = DeliveryPerson(i + self.num_customers, self,
                                                 self.service_center_top)
                self.grid.place_agent(
                    delivery_person, self.service_center_top.pos)
            else:
                delivery_person = DeliveryPerson(i + self.num_customers, self,
                                                 self.service_center_bottom)
                self.grid.place_agent(
                    delivery_person, self.service_center_bottom.pos)
            self.schedule.add(delivery_person)

        self.datacollector = DataCollector(
            model_reporters={
                "Hungry_Customers": lambda m: sum(1 for agent in m.schedule.agents
                                                  if isinstance(agent, Customer) and agent.is_hungry)
            }
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()
        time.sleep(0.1)


def agent_portrayal(agent):
    portrayal = {"Shape": "circle", "Filled": "true", "r": 0.4}

    if isinstance(agent, Customer):
        portrayal["Color"] = agent.color
        portrayal["Layer"] = 0
    elif isinstance(agent, DeliveryPerson):
        portrayal["Color"] = agent.color
        portrayal["Layer"] = 1
    elif isinstance(agent, ServiceCenter):
        portrayal["Shape"] = "rect"
        portrayal["Color"] = "black"
        portrayal["Layer"] = 5
        portrayal["w"] = 2
        portrayal["h"] = 2

    return portrayal


grid = CanvasGrid(agent_portrayal, 20, 20, 700, 500)

server = ModularServer(FoodDeliveryModel, [grid], "Food Delivery System", {
    "Customers": 100, "N_delivery_persons": 6, "width": 20, "height": 20
})
server.port = 8521

server.launch()
