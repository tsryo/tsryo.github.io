"use strict";

window.onload = function() {
  	const mainPanel = document.getElementById("right-panel").querySelector("table.panel-contents tr td");

  	const loadHome = function() {
		mainPanel.innerHTML = `
		<p style="font-size: 1.3em;">
			<i>Storytelling reveals meaning without committing the error of defining it.
			<br><p style="text-align: right; padding-right:3em;">-Hannah Arendt</p> </i>
		</p><br><br>
		<p>
			Research engineer working at the intersection of AI and clinical medicine.
			<br>
			PhD candidate at 
			<a href="https://www.amsterdamumc.org/" target="_blank">Amsterdam University Medical Center</a> / 
			<a href="https://www.uva.nl/" target="_blank">University of Amsterdam</a>, 
			with a dissertation on machine learning in cardiovascular disease — modelling, prediction, and phenotyping across multimodal and multi-centre data. Defence scheduled for June 2026.
			<br><br>

			Areas of interest include (but are not limited to): machine learning, natural language processing, federated learning, biostatistics, and multimodal modelling in regulated clinical environments. My work spans research design, validation, and translation into production-ready ML pipelines and privacy-preserving infrastructure.
			<br><br>

			Currently a research engineer in primary care data systems at Amsterdam UMC, designing reproducible ML pipelines for large-scale patient risk modelling. Previously part-time software engineer within Amsterdam UMC, building physician-facing clinical decision support systems.
			<br><br>

			Experienced in backend and middleware architectures, cloud-native systems, and DevOps practices in regulated environments. Rather than listing frameworks and languages, I prefer to choose the right instrument for the task at hand.
	    </p>`;

  	};
  	loadHome();


  	const loadLinks = function() {
  		mainPanel.innerHTML = `<ul>
  			  <li><a href="https://scholar.google.com/citations?user=qqIazjAAAAAJ">Google Scholar</a></li>
			  <li><a href="https://researchinformation.amsterdamumc.org/en/persons/tsvetan-yordanov">AUMC research profile</a></li>  
			  <li><a href="https://www.researchgate.net/profile/Tsvetan-Yordanov">ResearchGate</a></li>
			  <li><a href="https://orcid.org/0000-0003-0554-6646">ORCID iD</a></li>
			  <li><a href="https://www.linkedin.com/in/tsvetan-yordanov-998bb766/">LinkedIn</a></li>
			  <li><a href="https://github.com/tsryo">GitHub</a></li>
			</ul>`;
  	};

	window.navigation.addEventListener("navigate", (event) => {
		if(event.destination.url.endsWith("#home")) {
			loadHome();
		}

		else if(event.destination.url.endsWith("#links")) {
			loadLinks();
		}
	});

};

