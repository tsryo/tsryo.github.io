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
			  Experienced software engineer with a passion for research.<br>
	          Currently a fulltime PhD student at Amsterdam University Medical Center (AUMC).
	          <br>PhD project name 
	          <a href="https://www.amc.nl/web/research/departments/medical-informatics-1/projects.htm" target="_blank">AI4Cardiology</a>.<br> 
	          Areas of interest include (but are not limited to): machine learning, natural language processing, federated learning, biostatistics.<br>
	          Using my curiosity and knowledge to help bring forth improvements to humanity, one step at a time.
	          <br><br>
	          Currently a partime software engineer for the Netherlands Heart Registration (NHR).
	          Highly experienced in backend and middleware web appliation tehcnologies, and fairly experienced with frontend technologies.
	          I see little point in listing frameworks and programming langauges here, I would much rather say that I have the mentality of choosing the right
	          instrument for the task at hand. 
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

